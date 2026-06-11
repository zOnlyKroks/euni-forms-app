"""Django forms for the EVE Uni Forms app.

Form rendering/styling is handled in the templates via ``django_bootstrap5``
(`{% bootstrap_form %}`), so this module only defines fields, widgets and
validation — not CSS classes.
"""

# Django
from django import forms
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.safestring import mark_safe

# AA EVE Uni Forms
from euniforms.models import FieldChoice, Form, FormField

BOOLEAN_CHOICES = [("", "---------"), ("yes", _("Yes")), ("no", _("No"))]


class StarRatingWidget(forms.Widget):
    """Custom widget for clickable star ratings."""

    def __init__(self, max_rating=5, attrs=None):
        self.max_rating = max_rating
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = 0
        else:
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = 0

        if attrs is None:
            attrs = {}

        attrs['class'] = attrs.get('class', '') + ' star-rating-widget'
        attrs['data-max-rating'] = self.max_rating

        # Hidden input to store the actual value
        hidden_input = f'<input type="hidden" name="{name}" id="id_{name}" value="{value}">'

        # Star display
        stars_html = f'<div class="star-rating" data-field-name="{name}" data-current-rating="{value}">'
        for i in range(1, self.max_rating + 1):
            star_class = "star filled" if i <= value else "star empty"
            stars_html += f'<span class="{star_class}" data-rating="{i}">★</span>'
        stars_html += '</div>'

        # CSS and JavaScript for the stars
        style_and_script = f'''
        <style>
        .star-rating .star {{
            font-size: 1.5em;
            cursor: pointer;
            color: #ddd;
            transition: color 0.2s;
            margin-right: 2px;
        }}
        .star-rating .star.filled {{
            color: #ffd700;
        }}
        .star-rating .star:hover,
        .star-rating .star.hover {{
            color: #ffc107;
        }}
        .star-rating {{
            user-select: none;
            margin: 5px 0;
        }}
        </style>
        <script>
        (function() {{
            function initStarRating(container) {{
                const stars = container.querySelectorAll('.star');
                const fieldName = container.dataset.fieldName;
                const hiddenInput = document.querySelector('input[name="' + fieldName + '"]');

                stars.forEach((star, index) => {{
                    star.addEventListener('click', function() {{
                        const rating = parseInt(this.dataset.rating);
                        hiddenInput.value = rating;
                        updateStars(container, rating);
                    }});

                    star.addEventListener('mouseenter', function() {{
                        const rating = parseInt(this.dataset.rating);
                        highlightStars(container, rating);
                    }});
                }});

                container.addEventListener('mouseleave', function() {{
                    const currentRating = parseInt(hiddenInput.value) || 0;
                    updateStars(container, currentRating);
                }});
            }}

            function updateStars(container, rating) {{
                const stars = container.querySelectorAll('.star');
                stars.forEach((star, index) => {{
                    const starRating = parseInt(star.dataset.rating);
                    star.className = starRating <= rating ? 'star filled' : 'star empty';
                }});
            }}

            function highlightStars(container, rating) {{
                const stars = container.querySelectorAll('.star');
                stars.forEach((star, index) => {{
                    const starRating = parseInt(star.dataset.rating);
                    star.className = starRating <= rating ? 'star hover' : 'star empty';
                }});
            }}

            // Initialize when DOM is ready
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    const starContainer = document.querySelector('[data-field-name="{name}"]');
                    if (starContainer) initStarRating(starContainer);
                }});
            }} else {{
                const starContainer = document.querySelector('[data-field-name="{name}"]');
                if (starContainer) initStarRating(starContainer);
            }}
        }})();
        </script>
        '''

        return mark_safe(hidden_input + stars_html + style_and_script)


class CurrentDateWidget(forms.Widget):
    """Custom widget that always displays the current date."""

    def render(self, name, value, attrs=None, renderer=None):
        current_date = timezone.now().date()
        current_date_str = current_date.strftime("%Y-%m-%d")

        # Hidden input to store the current date value
        hidden_input = f'<input type="hidden" name="{name}" id="id_{name}" value="{current_date_str}">'

        # Display the current date in a disabled date input field
        display_input = f'''<input type="date" value="{current_date_str}"
                            readonly disabled
                            style="background-color: #f8f9fa; cursor: not-allowed; color: #6c757d;"
                            class="form-control">'''

        return mark_safe(hidden_input + display_input)


class SearchableCharacterWidget(forms.Widget):
    """Custom widget for searchable character selection."""

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = ""

        if attrs is None:
            attrs = {}

        # Get choices - ensure we have them
        choices = getattr(self, '_choices', [])

        # Get the display name for the selected value
        display_value = ""
        if value and choices:
            for choice_value, choice_label in choices:
                if choice_value == str(value):
                    display_value = choice_label
                    break

        widget_id = attrs.get('id', f'id_{name}')

        # Convert choices to JavaScript safely
        import json
        choices_js = json.dumps(choices)

        html = f'''
        <div class="searchable-character-picker" data-field-name="{name}">
            <input type="hidden" name="{name}" id="{widget_id}" value="{value}">
            <input type="text"
                   class="form-control searchable-input"
                   placeholder="Type character name to search... ({len(choices)} characters available)"
                   value="{display_value}"
                   autocomplete="off"
                   id="{widget_id}_search">
            <div class="search-results" id="{widget_id}_results" style="display: none;">
                <div class="no-results">Start typing to search characters...</div>
            </div>
        </div>

        <style>
        .searchable-character-picker {{
            position: relative;
            width: 100%;
        }}

        .searchable-character-picker .searchable-input {{
            color: #212529 !important;
            background-color: #ffffff !important;
            border: 1px solid #ced4da !important;
            border-radius: 0.375rem !important;
            padding: 0.375rem 0.75rem !important;
            font-size: 1rem !important;
            line-height: 1.5 !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }}

        .searchable-character-picker .searchable-input:focus {{
            color: #212529 !important;
            background-color: #ffffff !important;
            border-color: #86b7fe !important;
            outline: 0 !important;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25) !important;
        }}

        .searchable-character-picker .searchable-input::placeholder {{
            color: #6c757d !important;
            opacity: 1 !important;
        }}

        .searchable-character-picker .search-results {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ced4da;
            border-top: none;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            border-radius: 0 0 0.375rem 0.375rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .searchable-character-picker .search-result {{
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #f8f9fa;
            color: #212529 !important;
            background-color: white;
        }}

        .searchable-character-picker .search-result:hover {{
            background-color: #f8f9fa !important;
            color: #212529 !important;
        }}

        .searchable-character-picker .search-result.selected {{
            background-color: #007bff !important;
            color: white !important;
        }}

        .searchable-character-picker .no-results {{
            padding: 12px;
            color: #6c757d !important;
            font-style: italic;
        }}

        .searchable-input:focus + .search-results {{
            display: block !important;
        }}
        </style>

        <script>
        (function() {{
            const characterChoices = {choices_js};
            console.log('Character choices loaded:', characterChoices.length, 'characters');

            function initSearchableCharacterPicker(container) {{
                const fieldName = container.dataset.fieldName;
                const hiddenInput = container.querySelector('input[type="hidden"]');
                const searchInput = container.querySelector('.searchable-input');
                const resultsDiv = container.querySelector('.search-results');

                if (!characterChoices || characterChoices.length === 0) {{
                    searchInput.placeholder = 'No characters available';
                    return;
                }}

                let selectedIndex = -1;
                let filteredChoices = [];

                function showResults() {{
                    resultsDiv.style.display = 'block';
                }}

                function hideResults() {{
                    setTimeout(() => {{
                        resultsDiv.style.display = 'none';
                    }}, 200);
                }}

                function filterChoices(query) {{
                    if (!query.trim()) {{
                        filteredChoices = characterChoices.slice(0, 50); // Show first 50 when empty
                    }} else {{
                        filteredChoices = characterChoices.filter(choice => {{
                            const fullText = choice[1].toLowerCase();
                            const query_lower = query.toLowerCase();

                            // Extract character name (part before the first parenthesis)
                            const characterName = fullText.split('(')[0].trim();

                            // Search ONLY in character name, ignore parentheses content
                            return characterName.includes(query_lower);
                        }}).slice(0, 20); // Limit to 20 results
                    }}
                    renderResults();
                }}

                function renderResults() {{
                    if (filteredChoices.length === 0) {{
                        resultsDiv.innerHTML = '<div class="no-results">No characters found</div>';
                        return;
                    }}

                    let html = '';
                    filteredChoices.forEach((choice, index) => {{
                        const isSelected = index === selectedIndex ? 'selected' : '';
                        const escapedValue = choice[0].replace(/"/g, '&quot;');
                        const escapedLabel = choice[1].replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        html += `<div class="search-result ${{isSelected}}" data-value="${{escapedValue}}" data-index="${{index}}">${{escapedLabel}}</div>`;
                    }});
                    resultsDiv.innerHTML = html;

                    // Add click handlers to results
                    resultsDiv.querySelectorAll('.search-result').forEach(result => {{
                        result.addEventListener('click', function() {{
                            selectChoice(this.dataset.value, this.textContent);
                        }});
                    }});
                }}

                function selectChoice(value, label) {{
                    hiddenInput.value = value;
                    searchInput.value = label;
                    hideResults();
                    selectedIndex = -1;
                }}

                function updateSelection() {{
                    resultsDiv.querySelectorAll('.search-result').forEach((result, index) => {{
                        result.classList.toggle('selected', index === selectedIndex);
                    }});
                }}

                // Event listeners
                searchInput.addEventListener('input', function() {{
                    filterChoices(this.value);
                    selectedIndex = -1;
                    showResults();
                }});

                searchInput.addEventListener('focus', function() {{
                    filterChoices(this.value);
                    showResults();
                }});

                searchInput.addEventListener('blur', hideResults);

                searchInput.addEventListener('keydown', function(e) {{
                    if (!resultsDiv.style.display || resultsDiv.style.display === 'none') return;

                    if (e.key === 'ArrowDown') {{
                        e.preventDefault();
                        selectedIndex = Math.min(selectedIndex + 1, filteredChoices.length - 1);
                        updateSelection();
                    }} else if (e.key === 'ArrowUp') {{
                        e.preventDefault();
                        selectedIndex = Math.max(selectedIndex - 1, -1);
                        updateSelection();
                    }} else if (e.key === 'Enter') {{
                        e.preventDefault();
                        if (selectedIndex >= 0 && filteredChoices[selectedIndex]) {{
                            const choice = filteredChoices[selectedIndex];
                            selectChoice(choice[0], choice[1]);
                        }}
                    }} else if (e.key === 'Escape') {{
                        hideResults();
                        selectedIndex = -1;
                    }}
                }});

                // Initialize with empty search to show first results
                filterChoices('');
            }}

            // Initialize when DOM is ready
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    const container = document.querySelector('[data-field-name="{name}"]');
                    if (container) initSearchableCharacterPicker(container);
                }});
            }} else {{
                const container = document.querySelector('[data-field-name="{name}"]');
                if (container) initSearchableCharacterPicker(container);
            }}
        }})();
        </script>
        '''

        return mark_safe(html)

    def _get_choices_js(self):
        """Convert choices to JavaScript array format."""
        import json
        choices = getattr(self, '_choices', [])
        return json.dumps(choices)


class AjaxSearchableCharacterWidget(forms.Widget):
    """Optimized character picker widget using AJAX search instead of loading all users."""

    def render(self, name, value, attrs=None, renderer=None):
        from django.urls import reverse

        if value is None:
            value = ""

        if attrs is None:
            attrs = {}

        widget_id = attrs.get('id', f'id_{name}')

        # Get display name for existing value - minimal database query
        display_value = ""
        if value:
            display_value = self._get_display_name(value)

        # Get the search API URL
        search_url = reverse('euniforms:search_characters_api')

        html = f'''
        <div class="ajax-character-picker" data-field-name="{name}" data-search-url="{search_url}">
            <input type="hidden" name="{name}" id="{widget_id}" value="{value}">
            <input type="text"
                   class="form-control ajax-search-input"
                   placeholder="Type character name to search (min 2 characters)..."
                   value="{display_value}"
                   autocomplete="off"
                   id="{widget_id}_search">
            <div class="search-results ajax-results" id="{widget_id}_results" style="display: none;">
                <div class="loading">Loading...</div>
            </div>
        </div>

        <style>
        .ajax-character-picker {{
            position: relative;
            width: 100%;
        }}

        .ajax-search-input {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}

        .ajax-search-input:focus {{
            border-color: #007bff;
            outline: none;
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
        }}

        .ajax-results {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 4px 4px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .ajax-result-item {{
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
        }}

        .ajax-result-item:hover {{
            background-color: #f8f9fa;
        }}

        .ajax-result-item.selected {{
            background-color: #007bff;
            color: white;
        }}

        .loading, .no-results {{
            padding: 8px 12px;
            color: #6c757d;
            font-style: italic;
        }}
        </style>

        <script>
        (function() {{
            function initAjaxCharacterPicker(container) {{
                const fieldName = container.dataset.fieldName;
                const searchUrl = container.dataset.searchUrl;
                const hiddenInput = container.querySelector('input[type="hidden"]');
                const searchInput = container.querySelector('.ajax-search-input');
                const resultsDiv = container.querySelector('.ajax-results');

                let searchTimeout;
                let currentQuery = '';
                let selectedIndex = -1;
                let results = [];

                function showResults() {{
                    resultsDiv.style.display = 'block';
                }}

                function hideResults() {{
                    setTimeout(() => {{
                        resultsDiv.style.display = 'none';
                    }}, 150);
                }}

                function updateSelection() {{
                    const items = resultsDiv.querySelectorAll('.ajax-result-item');
                    items.forEach((item, index) => {{
                        if (index === selectedIndex) {{
                            item.classList.add('selected');
                        }} else {{
                            item.classList.remove('selected');
                        }}
                    }});
                }}

                function selectResult(result) {{
                    hiddenInput.value = result.id;
                    searchInput.value = result.display;
                    hideResults();
                }}

                function performSearch(query) {{
                    if (query.length < 2) {{
                        resultsDiv.innerHTML = '<div class="no-results">Type at least 2 characters to search</div>';
                        showResults();
                        return;
                    }}

                    resultsDiv.innerHTML = '<div class="loading">Searching...</div>';
                    showResults();

                    fetch(`${{searchUrl}}?q=${{encodeURIComponent(query)}}&limit=20`)
                        .then(response => response.json())
                        .then(data => {{
                            results = data.results;
                            selectedIndex = -1;

                            if (results.length === 0) {{
                                resultsDiv.innerHTML = '<div class="no-results">No characters found</div>';
                            }} else {{
                                const html = results.map(result =>
                                    `<div class="ajax-result-item" data-id="${{result.id}}">${{result.display}}</div>`
                                ).join('');
                                resultsDiv.innerHTML = html;

                                // Add click handlers
                                resultsDiv.querySelectorAll('.ajax-result-item').forEach((item, index) => {{
                                    item.addEventListener('click', () => {{
                                        selectResult(results[index]);
                                    }});
                                }});
                            }}
                        }})
                        .catch(error => {{
                            console.error('Search error:', error);
                            resultsDiv.innerHTML = '<div class="no-results">Search error occurred</div>';
                        }});
                }}

                // Event handlers
                searchInput.addEventListener('input', (e) => {{
                    const query = e.target.value.trim();
                    currentQuery = query;

                    clearTimeout(searchTimeout);
                    searchTimeout = setTimeout(() => {{
                        if (currentQuery === query) {{
                            performSearch(query);
                        }}
                    }}, 300); // Debounce search
                }});

                searchInput.addEventListener('focus', () => {{
                    if (currentQuery.length >= 2) {{
                        showResults();
                    }}
                }});

                searchInput.addEventListener('blur', hideResults);

                searchInput.addEventListener('keydown', (e) => {{
                    const items = resultsDiv.querySelectorAll('.ajax-result-item');

                    if (e.key === 'ArrowDown') {{
                        e.preventDefault();
                        selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                        updateSelection();
                    }} else if (e.key === 'ArrowUp') {{
                        e.preventDefault();
                        selectedIndex = Math.max(selectedIndex - 1, -1);
                        updateSelection();
                    }} else if (e.key === 'Enter') {{
                        e.preventDefault();
                        if (selectedIndex >= 0 && selectedIndex < results.length) {{
                            selectResult(results[selectedIndex]);
                        }}
                    }} else if (e.key === 'Escape') {{
                        hideResults();
                    }}
                }});
            }}

            // Initialize when DOM is ready
            document.addEventListener('DOMContentLoaded', function() {{
                const container = document.querySelector('[data-field-name="{name}"]');
                if (container) initAjaxCharacterPicker(container);
            }});

            // Also initialize immediately in case DOM is already ready
            const container = document.querySelector('[data-field-name="{name}"]');
            if (container) initAjaxCharacterPicker(container);
        }})();
        </script>
        '''

        return mark_safe(html)

    def _get_display_name(self, value):
        """Get display name for a selected value - minimal database query."""
        if not value:
            return ""

        try:
            from django.contrib.auth.models import User

            if value.startswith('main_'):
                char_id = value.replace('main_', '')
                # Query only the specific main character
                user = User.objects.select_related('profile__main_character').filter(
                    profile__main_character__character_id=char_id,
                    is_active=True
                ).first()
                if user and user.profile.main_character:
                    char = user.profile.main_character
                    return f"{char.character_name} (Main - {user.username})"

            elif value.startswith('char_'):
                char_id = value.replace('char_', '')
                # Query only the specific character
                user = User.objects.select_related('character_ownerships__character').filter(
                    character_ownerships__character__character_id=char_id,
                    is_active=True
                ).first()
                if user:
                    ownership = user.character_ownerships.filter(character__character_id=char_id).first()
                    if ownership:
                        char = ownership.character
                        return f"{char.character_name} (Alt - {user.username})"

            elif value.startswith('user_'):
                user_id = value.replace('user_', '')
                user = User.objects.filter(id=user_id, is_active=True).first()
                if user:
                    return f"{user.username} (No characters)"

        except Exception:
            pass  # Fallback to empty display name

        return ""


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
            "collaborator_groups",
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
            "collaborator_groups": forms.CheckboxSelectMultiple(
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
        self.fields["collaborator_groups"].queryset = Group.objects.order_by("name")

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
        self._user_names: dict[str, str] = {}
        # Performance optimization: Don't build user choices upfront for AJAX USER_PICKER
        self._user_choices = None

        for question in form_obj.fields.all().prefetch_related("choices"):
            name = f"field_{question.pk}"
            self.fields[name] = self._build_field(question)
            self._field_map[name] = question

    def _build_character_choices(self, user) -> list[tuple[str, str]]:
        """Choices of the user's SSO-verified characters (including main and all alts)."""
        choices: list[tuple[str, str]] = []
        if user is None:
            return choices

        seen: set[str] = set()

        # First, ensure the main character is always included
        if hasattr(user, "profile") and user.profile and user.profile.main_character:
            main_char = user.profile.main_character
            main_cid = str(main_char.character_id)
            seen.add(main_cid)
            choices.append((main_cid, f"{main_char.character_name} (Main)"))
            self._character_names[main_cid] = main_char.character_name

        # Then add all other SSO-verified characters (alts)
        if hasattr(user, "character_ownerships"):
            ownerships = user.character_ownerships.select_related("character").all()
            for ownership in ownerships:
                character = ownership.character
                cid = str(character.character_id)
                if cid in seen:
                    continue
                seen.add(cid)
                choices.append((cid, character.character_name))
                self._character_names[cid] = character.character_name

        # Sort choices by character name (case-insensitive)
        choices.sort(key=lambda choice: choice[1].lower())
        return choices

    def _build_user_choices(self) -> list[tuple[str, str]]:
        """Choices of all characters from all users in the system."""
        choices: list[tuple[str, str]] = []

        # Get all active users and their characters
        users = User.objects.filter(is_active=True).prefetch_related('character_ownerships__character').order_by('username')

        for user in users:
            # Add the main character first if available
            if hasattr(user, 'profile') and user.profile and user.profile.main_character:
                main_char = user.profile.main_character
                main_char_id = f"main_{main_char.character_id}"
                display_name = f"{main_char.character_name} (Main - {user.username})"
                choices.append((main_char_id, display_name))
                self._user_names[main_char_id] = main_char.character_name

            # Add all other SSO-verified characters for this user
            if hasattr(user, 'character_ownerships'):
                ownerships = user.character_ownerships.select_related('character').all()
                for ownership in ownerships:
                    character = ownership.character
                    char_id = f"char_{character.character_id}"

                    # Skip if this is already the main character
                    if (hasattr(user, 'profile') and user.profile and user.profile.main_character and
                        character.character_id == user.profile.main_character.character_id):
                        continue

                    display_name = f"{character.character_name} (Alt - {user.username})"
                    choices.append((char_id, display_name))
                    self._user_names[char_id] = character.character_name

            # If no characters found, add the user by username as fallback
            if not hasattr(user, 'character_ownerships') or not user.character_ownerships.exists():
                if not (hasattr(user, 'profile') and user.profile and user.profile.main_character):
                    user_id = f"user_{user.id}"
                    display_name = f"{user.username} (No characters)"
                    choices.append((user_id, display_name))
                    self._user_names[user_id] = user.username

        # Sort choices by character/user name (case-insensitive)
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
        if question.field_type == FieldType.FREE_TEXT:
            return forms.CharField(
                max_length=1000,
                widget=forms.Textarea(attrs={"rows": 6, "maxlength": "1000"}),
                **common
            )
        if question.field_type == FieldType.NUMBER:
            return forms.DecimalField(**common)
        if question.field_type == FieldType.DATE_CURRENT:
            # Date field that always uses current date (read-only display)
            return forms.CharField(
                widget=CurrentDateWidget(),
                **common
            )
        if question.field_type == FieldType.DATETIME:
            # DateTime field for both date and time selection
            return forms.DateTimeField(
                widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
                **common
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
        if question.field_type == FieldType.USER_PICKER:
            # Use optimized AJAX widget instead of loading all users upfront
            widget = AjaxSearchableCharacterWidget()
            return forms.CharField(
                widget=widget, **common
            )
        if question.field_type == FieldType.URL:
            return forms.URLField(**common)
        if question.field_type == FieldType.ISK_AMOUNT:
            return forms.DecimalField(
                decimal_places=2,
                max_digits=20,
                min_value=0,
                widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
                **common
            )
        if question.field_type == FieldType.RATING_5:
            return forms.IntegerField(
                min_value=1,
                max_value=5,
                widget=StarRatingWidget(max_rating=5),
                **common
            )
        if question.field_type == FieldType.RATING_10:
            return forms.IntegerField(
                min_value=1,
                max_value=10,
                widget=StarRatingWidget(max_rating=10),
                **common
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
        if question.field_type == FieldType.DATE_CURRENT:
            # Always use current date regardless of user input
            return timezone.now().date().isoformat()
        if question.field_type == FieldType.DATETIME:
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
        if question.field_type == FieldType.USER_PICKER:
            uid = str(raw)
            character_name = self._user_names.get(uid, "")

            # Extract the actual ID and type from prefixed format
            if uid.startswith("main_"):
                char_id = uid.replace("main_", "")
                return {
                    "character_id": int(char_id),
                    "character_name": character_name,
                    "type": "main"
                }
            elif uid.startswith("char_"):
                char_id = uid.replace("char_", "")
                return {
                    "character_id": int(char_id),
                    "character_name": character_name,
                    "type": "alt"
                }
            elif uid.startswith("user_"):
                user_id = uid.replace("user_", "")
                return {
                    "user_id": int(user_id),
                    "username": character_name,
                    "type": "user"
                }
            else:
                # Fallback for any unexpected format
                return {
                    "raw_id": uid,
                    "name": character_name,
                    "type": "unknown"
                }
        if question.field_type == FieldType.URL:
            return str(raw)
        if question.field_type == FieldType.ISK_AMOUNT:
            # Store as float with proper precision
            return float(raw)
        if question.field_type in (FieldType.RATING_5, FieldType.RATING_10):
            # Store as integer rating
            return int(raw)
        return raw
