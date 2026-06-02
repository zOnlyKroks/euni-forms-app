"""Django forms for the EVE Uni Forms app.

Form rendering/styling is handled in the templates via ``django_bootstrap5``
(`{% bootstrap_form %}`), so this module only defines fields, widgets and
validation — not CSS classes.
"""

# Django
from django import forms
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

# AA EVE Uni Forms
from euniforms.models import FieldChoice, Form, FormField

BOOLEAN_CHOICES = [("", "---------"), ("yes", _("Yes")), ("no", _("No"))]


class FormModelForm(forms.ModelForm):
    """Create / edit a form's metadata. Questions are managed on a separate page."""

    # Dynamic field for state selection - choices are set in __init__
    restricted_states = forms.MultipleChoiceField(
        choices=[],  # Will be populated dynamically
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=False,
        help_text=_("Select which user states can fill this form. States are automatically detected from your existing groups.")
    )

    class Meta:
        model = Form
        fields = [
            "title",
            "description",
            "introduction_text",
            "status",
            "restricted_groups",
            "restrict_by_group",
            "restricted_states",
            "restrict_by_state",
            "restriction_logic",
            "viewer_groups",
            "answer_limit_type",
            "answer_limit",
            "limit_window_days",
            "notify_on_submit",
            "discord_webhook_url",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "introduction_text": forms.Textarea(attrs={"rows": 4}),
            "restricted_groups": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"}
            ),
            "viewer_groups": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"}
            ),
            "answer_limit_type": forms.Select(
                attrs={"class": "form-select", "id": "id_answer_limit_type"}
            ),
            "answer_limit": forms.NumberInput(
                attrs={"min": "1", "max": "999", "class": "form-control"}
            ),
            "limit_window_days": forms.NumberInput(
                attrs={"min": "1", "max": "365", "class": "form-control"}
            ),
            "discord_webhook_url": forms.URLInput(
                attrs={"placeholder": "https://discord.com/api/webhooks/..."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["restricted_groups"].queryset = Group.objects.order_by("name")
        self.fields["viewer_groups"].queryset = Group.objects.order_by("name")

        # Dynamically populate state choices based on existing groups
        self.fields['restricted_states'].choices = Form.get_state_choices()

        # Pre-populate restricted_states field if form instance exists
        if self.instance.pk and self.instance.restricted_states:
            self.fields['restricted_states'].initial = self.instance.restricted_states

        # Configure answer limit field help text and requirements
        self.fields['answer_limit_type'].help_text = _("Control how many times each user can submit this form.")
        self.fields['answer_limit'].help_text = _("Maximum submissions per user (only used with 'Limited submissions per account').")
        self.fields['limit_window_days'].help_text = _("Optional: Reset the limit every N days. Leave empty for no time limit.")

    def clean(self):
        """Validate answer limit configuration."""
        cleaned_data = super().clean()
        answer_limit_type = cleaned_data.get('answer_limit_type')
        answer_limit = cleaned_data.get('answer_limit')

        # If LIMITED_PER_ACCOUNT is selected, answer_limit is required
        if answer_limit_type == Form.AnswerLimitType.LIMITED_PER_ACCOUNT:
            if not answer_limit or answer_limit <= 0:
                self.add_error('answer_limit', _('You must specify a valid answer limit when using "Limited submissions per account".'))

        return cleaned_data

    def save(self, commit=True):
        """Save the form instance, properly handling the restricted_states JSONField."""
        instance = super().save(commit=False)

        # Convert MultipleChoiceField selection to JSON list
        if 'restricted_states' in self.cleaned_data:
            instance.restricted_states = list(self.cleaned_data['restricted_states'])

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class FormFieldModelForm(forms.ModelForm):
    """Create / edit a single question on a form."""

    choices_text = forms.CharField(
        label=_("Choices"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text=_("One option per line. Only used for single/multiple choice fields."),
    )

    class Meta:
        model = FormField
        fields = ["label", "help_text", "field_type", "required"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["choices_text"].initial = "\n".join(
                self.instance.choices.values_list("value", flat=True)
            )

    @staticmethod
    def _parse_choices(text: str) -> list[str]:
        return [line.strip() for line in (text or "").splitlines() if line.strip()]

    def clean(self):
        cleaned = super().clean()
        choices = self._parse_choices(cleaned.get("choices_text", ""))
        if cleaned.get("field_type") in (
            FormField.FieldType.SINGLE_CHOICE,
            FormField.FieldType.MULTI_CHOICE,
        ) and not choices:
            self.add_error(
                "choices_text", _("Choice fields need at least one option.")
            )
        cleaned["parsed_choices"] = choices
        return cleaned

    def save_choices(self, field: FormField) -> None:
        """Replace ``field``'s choices with the parsed list. Call after ``save()``."""
        field.choices.all().delete()
        if field.is_choice_type:
            FieldChoice.objects.bulk_create(
                FieldChoice(field=field, order=index, value=value)
                for index, value in enumerate(self.cleaned_data.get("parsed_choices", []))
            )


class DynamicFillForm(forms.Form):
    """A form whose fields are built at runtime from a :class:`Form`'s questions."""

    def __init__(self, *args, form_obj: Form, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_obj = form_obj
        self.user = user
        self._field_map: dict[str, FormField] = {}
        self._character_names: dict[str, str] = {}
        self._character_choices = self._build_character_choices(user)

        for question in form_obj.fields.all().prefetch_related("choices"):
            name = f"field_{question.pk}"
            self.fields[name] = self._build_field(question)
            self._field_map[name] = question

    def _build_character_choices(self, user) -> list[tuple[str, str]]:
        """Choices of the user's SSO-verified characters (their alts)."""
        choices: list[tuple[str, str]] = []
        if user is None or not hasattr(user, "character_ownerships"):
            return choices
        seen: set[str] = set()
        ownerships = user.character_ownerships.select_related("character").all()
        for ownership in ownerships:
            character = ownership.character
            cid = str(character.character_id)
            if cid in seen:
                continue
            seen.add(cid)
            choices.append((cid, character.character_name))
            self._character_names[cid] = character.character_name
        choices.sort(key=lambda choice: choice[1].lower())
        return choices

    def _build_field(self, question: FormField) -> forms.Field:
        FieldType = FormField.FieldType
        common = {
            "label": question.label,
            "required": question.required,
            "help_text": question.help_text,
        }

        if question.field_type == FieldType.SHORT_TEXT:
            return forms.CharField(max_length=1000, **common)
        if question.field_type == FieldType.LONG_TEXT:
            return forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), **common)
        if question.field_type == FieldType.FREE_TEXT:
            return forms.CharField(
                max_length=1000,
                widget=forms.Textarea(attrs={"rows": 6, "maxlength": "1000"}),
                **common
            )
        if question.field_type == FieldType.NUMBER:
            return forms.DecimalField(**common)
        if question.field_type == FieldType.DATE:
            return forms.DateField(
                widget=forms.DateInput(attrs={"type": "date"}), **common
            )
        if question.field_type == FieldType.BOOLEAN:
            return forms.ChoiceField(choices=BOOLEAN_CHOICES, **common)
        if question.field_type == FieldType.SINGLE_CHOICE:
            options = [(c.value, c.value) for c in question.choices.all()]
            return forms.ChoiceField(choices=[("", "---------")] + options, **common)
        if question.field_type == FieldType.MULTI_CHOICE:
            options = [(c.value, c.value) for c in question.choices.all()]
            return forms.MultipleChoiceField(
                choices=options, widget=forms.CheckboxSelectMultiple, **common
            )
        if question.field_type == FieldType.EVE_CHARACTER:
            return forms.ChoiceField(
                choices=[("", "---------")] + self._character_choices, **common
            )
        return forms.CharField(**common)  # pragma: no cover - defensive

    def iter_answers(self):
        """Yield ``(FormField, json_value)`` pairs. Call after ``is_valid()``."""
        for name, question in self._field_map.items():
            yield question, self._to_json_value(question, self.cleaned_data.get(name))

    def _to_json_value(self, question: FormField, raw):
        FieldType = FormField.FieldType
        if raw in (None, "", [], ()):
            return None
        if question.field_type == FieldType.NUMBER:
            return int(raw) if raw == raw.to_integral_value() else float(raw)
        if question.field_type == FieldType.DATE:
            return raw.isoformat()
        if question.field_type == FieldType.BOOLEAN:
            return raw == "yes"
        if question.field_type == FieldType.MULTI_CHOICE:
            return list(raw)
        if question.field_type == FieldType.EVE_CHARACTER:
            cid = str(raw)
            return {
                "character_id": int(cid),
                "character_name": self._character_names.get(cid, ""),
            }
        return raw
