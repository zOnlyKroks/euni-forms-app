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

    class Meta:
        model = Form
        fields = [
            "title",
            "description",
            "introduction_text",
            "status",
            "restricted_groups",
            "viewer_groups",
            "allow_multiple",
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
            "discord_webhook_url": forms.URLInput(
                attrs={"placeholder": "https://discord.com/api/webhooks/..."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["restricted_groups"].queryset = Group.objects.order_by("name")
        self.fields["viewer_groups"].queryset = Group.objects.order_by("name")


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
