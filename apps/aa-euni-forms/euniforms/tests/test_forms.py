"""Test cases for euniforms forms."""

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django import forms
from unittest.mock import Mock, MagicMock
from decimal import Decimal
import datetime

from euniforms.models import Form, FormField, FieldChoice
from euniforms.forms import FormModelForm, FormFieldModelForm, DynamicFillForm


class FormModelFormTestCase(TestCase):
    """Test cases for the FormModelForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.group1 = Group.objects.create(name='Group 1')
        self.group2 = Group.objects.create(name='Group 2')

    def test_form_creation_valid(self):
        """Test valid form creation."""
        form_data = {
            'title': 'Test Form',
            'description': 'A test form',
            'status': Form.Status.DRAFT,
            'allow_multiple': False,
            'notify_on_submit': True,
        }

        form = FormModelForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Save and check
        form_obj = form.save(commit=False)
        form_obj.created_by = self.user
        form_obj.save()
        form.save_m2m()

        self.assertEqual(form_obj.title, 'Test Form')
        self.assertEqual(form_obj.description, 'A test form')
        self.assertEqual(form_obj.status, Form.Status.DRAFT)

    def test_form_creation_invalid_missing_title(self):
        """Test form creation with missing title."""
        form_data = {
            'description': 'A test form',
            'status': Form.Status.DRAFT,
        }

        form = FormModelForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_form_with_groups(self):
        """Test form creation with restricted and viewer groups."""
        form_data = {
            'title': 'Test Form',
            'description': 'A test form',
            'status': Form.Status.OPEN,
            'restricted_groups': [self.group1.pk],
            'viewer_groups': [self.group2.pk],
            'allow_multiple': False,
            'notify_on_submit': True,
        }

        form = FormModelForm(data=form_data)
        self.assertTrue(form.is_valid())

        form_obj = form.save(commit=False)
        form_obj.created_by = self.user
        form_obj.save()
        form.save_m2m()

        self.assertIn(self.group1, form_obj.restricted_groups.all())
        self.assertIn(self.group2, form_obj.viewer_groups.all())

    def test_form_with_discord_webhook(self):
        """Test form creation with Discord webhook URL."""
        form_data = {
            'title': 'Test Form',
            'description': 'A test form',
            'status': Form.Status.OPEN,
            'discord_webhook_url': 'https://discord.com/api/webhooks/123456789/test-token',
            'allow_multiple': False,
            'notify_on_submit': True,
        }

        form = FormModelForm(data=form_data)
        self.assertTrue(form.is_valid())

        form_obj = form.save(commit=False)
        form_obj.created_by = self.user
        form_obj.save()

        self.assertEqual(
            form_obj.discord_webhook_url,
            'https://discord.com/api/webhooks/123456789/test-token'
        )

    def test_form_edit_existing(self):
        """Test editing an existing form."""
        # Create form
        form_obj = Form.objects.create(
            title='Original Title',
            description='Original description',
            created_by=self.user
        )

        # Edit form
        form_data = {
            'title': 'Updated Title',
            'description': 'Updated description',
            'status': Form.Status.OPEN,
            'allow_multiple': True,
            'notify_on_submit': False,
        }

        form = FormModelForm(data=form_data, instance=form_obj)
        self.assertTrue(form.is_valid())

        updated_form = form.save()
        self.assertEqual(updated_form.title, 'Updated Title')
        self.assertEqual(updated_form.description, 'Updated description')
        self.assertTrue(updated_form.allow_multiple)
        self.assertFalse(updated_form.notify_on_submit)

    def test_groups_queryset_ordering(self):
        """Test that groups are ordered by name."""
        Group.objects.create(name='Zebra Group')
        Group.objects.create(name='Alpha Group')

        form = FormModelForm()

        restricted_groups_choices = list(form.fields['restricted_groups'].queryset)
        group_names = [group.name for group in restricted_groups_choices]

        # Should be ordered alphabetically
        self.assertEqual(group_names, sorted(group_names))


class FormFieldModelFormTestCase(TestCase):
    """Test cases for the FormFieldModelForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.form = Form.objects.create(
            title='Test Form',
            created_by=self.user
        )

    def test_field_creation_text(self):
        """Test creating a text field."""
        field_data = {
            'label': 'Text Question',
            'help_text': 'Enter some text',
            'field_type': FormField.FieldType.SHORT_TEXT,
            'required': True,
        }

        form = FormFieldModelForm(data=field_data)
        self.assertTrue(form.is_valid())

        field = form.save(commit=False)
        field.form = self.form
        field.save()

        self.assertEqual(field.label, 'Text Question')
        self.assertEqual(field.field_type, FormField.FieldType.SHORT_TEXT)
        self.assertTrue(field.required)

    def test_field_creation_single_choice(self):
        """Test creating a single choice field with choices."""
        field_data = {
            'label': 'Choice Question',
            'field_type': FormField.FieldType.SINGLE_CHOICE,
            'required': True,
            'choices_text': 'Option 1\nOption 2\nOption 3',
        }

        form = FormFieldModelForm(data=field_data)
        self.assertTrue(form.is_valid())

        field = form.save(commit=False)
        field.form = self.form
        field.save()
        form.save_choices(field)

        self.assertEqual(field.field_type, FormField.FieldType.SINGLE_CHOICE)

        # Check choices were created
        choices = list(field.choices.values_list('value', flat=True))
        self.assertEqual(choices, ['Option 1', 'Option 2', 'Option 3'])

    def test_field_creation_multi_choice(self):
        """Test creating a multiple choice field."""
        field_data = {
            'label': 'Multi Choice Question',
            'field_type': FormField.FieldType.MULTI_CHOICE,
            'required': False,
            'choices_text': 'Choice A\nChoice B\nChoice C',
        }

        form = FormFieldModelForm(data=field_data)
        self.assertTrue(form.is_valid())

        field = form.save(commit=False)
        field.form = self.form
        field.save()
        form.save_choices(field)

        choices = list(field.choices.values_list('value', 'order'))
        expected = [('Choice A', 0), ('Choice B', 1), ('Choice C', 2)]
        self.assertEqual(choices, expected)

    def test_field_creation_choice_empty_choices(self):
        """Test that choice fields require choices."""
        field_data = {
            'label': 'Choice Question',
            'field_type': FormField.FieldType.SINGLE_CHOICE,
            'required': True,
            'choices_text': '',  # No choices provided
        }

        form = FormFieldModelForm(data=field_data)
        self.assertFalse(form.is_valid())
        self.assertIn('choices_text', form.errors)

    def test_field_creation_choice_whitespace_handling(self):
        """Test that whitespace in choices is handled correctly."""
        field_data = {
            'label': 'Choice Question',
            'field_type': FormField.FieldType.SINGLE_CHOICE,
            'required': True,
            'choices_text': '  Option 1  \n\n  Option 2  \n   \nOption 3\n\n',
        }

        form = FormFieldModelForm(data=field_data)
        self.assertTrue(form.is_valid())

        # Check parsed choices
        parsed_choices = form.cleaned_data['parsed_choices']
        self.assertEqual(parsed_choices, ['Option 1', 'Option 2', 'Option 3'])

    def test_field_creation_non_choice_with_choices(self):
        """Test that non-choice fields ignore choices_text."""
        field_data = {
            'label': 'Text Question',
            'field_type': FormField.FieldType.SHORT_TEXT,
            'required': True,
            'choices_text': 'This should be ignored',
        }

        form = FormFieldModelForm(data=field_data)
        self.assertTrue(form.is_valid())  # Should be valid even with choices_text

    def test_field_edit_with_existing_choices(self):
        """Test editing a field that already has choices."""
        # Create field with choices
        field = FormField.objects.create(
            form=self.form,
            label='Original Question',
            field_type=FormField.FieldType.SINGLE_CHOICE
        )
        FieldChoice.objects.create(field=field, order=0, value='Original Option 1')
        FieldChoice.objects.create(field=field, order=1, value='Original Option 2')

        # Initialize form with existing field
        form = FormFieldModelForm(instance=field)
        initial_choices = form.fields['choices_text'].initial
        self.assertEqual(initial_choices, 'Original Option 1\nOriginal Option 2')

        # Update the field
        field_data = {
            'label': 'Updated Question',
            'field_type': FormField.FieldType.SINGLE_CHOICE,
            'required': True,
            'choices_text': 'New Option 1\nNew Option 2\nNew Option 3',
        }

        form = FormFieldModelForm(data=field_data, instance=field)
        self.assertTrue(form.is_valid())

        updated_field = form.save()
        form.save_choices(updated_field)

        # Check that old choices were replaced
        choices = list(updated_field.choices.values_list('value', flat=True))
        self.assertEqual(choices, ['New Option 1', 'New Option 2', 'New Option 3'])

    def test_parse_choices_static_method(self):
        """Test the _parse_choices static method."""
        # Test normal case
        choices = FormFieldModelForm._parse_choices('Option 1\nOption 2\nOption 3')
        self.assertEqual(choices, ['Option 1', 'Option 2', 'Option 3'])

        # Test with empty lines and whitespace
        choices = FormFieldModelForm._parse_choices('  Option 1  \n\n  Option 2  \n\n\n')
        self.assertEqual(choices, ['Option 1', 'Option 2'])

        # Test empty string
        choices = FormFieldModelForm._parse_choices('')
        self.assertEqual(choices, [])

        # Test None
        choices = FormFieldModelForm._parse_choices(None)
        self.assertEqual(choices, [])

    def test_save_choices_non_choice_field(self):
        """Test that save_choices doesn't create choices for non-choice fields."""
        field = FormField.objects.create(
            form=self.form,
            label='Text Question',
            field_type=FormField.FieldType.SHORT_TEXT
        )

        field_data = {
            'label': 'Text Question',
            'field_type': FormField.FieldType.SHORT_TEXT,
            'required': True,
            'choices_text': 'Should be ignored',
        }

        form = FormFieldModelForm(data=field_data, instance=field)
        self.assertTrue(form.is_valid())

        form.save()
        form.save_choices(field)

        # Should have no choices
        self.assertEqual(field.choices.count(), 0)


class DynamicFillFormTestCase(TestCase):
    """Test cases for the DynamicFillForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.form = Form.objects.create(
            title='Test Form',
            created_by=self.user
        )

        # Create various field types
        self.text_field = FormField.objects.create(
            form=self.form,
            label='Text Question',
            field_type=FormField.FieldType.SHORT_TEXT,
            order=1
        )

        self.number_field = FormField.objects.create(
            form=self.form,
            label='Number Question',
            field_type=FormField.FieldType.NUMBER,
            order=2
        )

        self.boolean_field = FormField.objects.create(
            form=self.form,
            label='Boolean Question',
            field_type=FormField.FieldType.BOOLEAN,
            order=3
        )

        self.date_field = FormField.objects.create(
            form=self.form,
            label='Date Question',
            field_type=FormField.FieldType.DATE,
            order=4
        )

        self.choice_field = FormField.objects.create(
            form=self.form,
            label='Choice Question',
            field_type=FormField.FieldType.SINGLE_CHOICE,
            order=5
        )
        FieldChoice.objects.create(field=self.choice_field, order=0, value='Option 1')
        FieldChoice.objects.create(field=self.choice_field, order=1, value='Option 2')

        self.multi_choice_field = FormField.objects.create(
            form=self.form,
            label='Multi Choice Question',
            field_type=FormField.FieldType.MULTI_CHOICE,
            order=6
        )
        FieldChoice.objects.create(field=self.multi_choice_field, order=0, value='Choice A')
        FieldChoice.objects.create(field=self.multi_choice_field, order=1, value='Choice B')

    def test_dynamic_form_creation(self):
        """Test that dynamic form creates appropriate fields."""
        form = DynamicFillForm(form_obj=self.form, user=self.user)

        # Check that fields were created
        expected_fields = [
            f'field_{self.text_field.pk}',
            f'field_{self.number_field.pk}',
            f'field_{self.boolean_field.pk}',
            f'field_{self.date_field.pk}',
            f'field_{self.choice_field.pk}',
            f'field_{self.multi_choice_field.pk}',
        ]

        for field_name in expected_fields:
            self.assertIn(field_name, form.fields)

    def test_text_field_rendering(self):
        """Test text field creation and validation."""
        form = DynamicFillForm(form_obj=self.form, user=self.user)
        field_name = f'field_{self.text_field.pk}'

        # Check field type and properties
        field = form.fields[field_name]
        self.assertIsInstance(field, forms.CharField)
        self.assertEqual(field.label, 'Text Question')
        self.assertEqual(field.max_length, 1000)

    def test_number_field_rendering(self):
        """Test number field creation and validation."""
        form = DynamicFillForm(form_obj=self.form, user=self.user)
        field_name = f'field_{self.number_field.pk}'

        field = form.fields[field_name]
        self.assertIsInstance(field, forms.DecimalField)

    def test_boolean_field_rendering(self):
        """Test boolean field creation."""
        form = DynamicFillForm(form_obj=self.form, user=self.user)
        field_name = f'field_{self.boolean_field.pk}'

        field = form.fields[field_name]
        self.assertIsInstance(field, forms.ChoiceField)

        # Check choices include yes/no options
        choice_values = [choice[0] for choice in field.choices]
        self.assertIn('yes', choice_values)
        self.assertIn('no', choice_values)

    def test_date_field_rendering(self):
        """Test date field creation."""
        form = DynamicFillForm(form_obj=self.form, user=self.user)
        field_name = f'field_{self.date_field.pk}'

        field = form.fields[field_name]
        self.assertIsInstance(field, forms.DateField)

    def test_choice_field_rendering(self):
        """Test single choice field creation."""
        form = DynamicFillForm(form_obj=self.form, user=self.user)
        field_name = f'field_{self.choice_field.pk}'

        field = form.fields[field_name]
        self.assertIsInstance(field, forms.ChoiceField)

        # Check choices were included
        choice_values = [choice[1] for choice in field.choices[1:]]  # Skip empty option
        self.assertEqual(choice_values, ['Option 1', 'Option 2'])

    def test_multi_choice_field_rendering(self):
        """Test multiple choice field creation."""
        form = DynamicFillForm(form_obj=self.form, user=self.user)
        field_name = f'field_{self.multi_choice_field.pk}'

        field = form.fields[field_name]
        self.assertIsInstance(field, forms.MultipleChoiceField)

        choice_values = [choice[1] for choice in field.choices]
        self.assertEqual(choice_values, ['Choice A', 'Choice B'])

    def test_character_field_without_ownerships(self):
        """Test EVE character field when user has no character ownerships."""
        char_field = FormField.objects.create(
            form=self.form,
            label='Character Question',
            field_type=FormField.FieldType.EVE_CHARACTER,
            order=7
        )

        form = DynamicFillForm(form_obj=self.form, user=self.user)
        field_name = f'field_{char_field.pk}'

        field = form.fields[field_name]
        self.assertIsInstance(field, forms.ChoiceField)

        # Should only have empty option since no characters
        self.assertEqual(len(field.choices), 1)
        self.assertEqual(field.choices[0][0], '')

    def test_character_field_with_mock_ownerships(self):
        """Test EVE character field with mock character ownerships."""
        char_field = FormField.objects.create(
            form=self.form,
            label='Character Question',
            field_type=FormField.FieldType.EVE_CHARACTER,
            order=7
        )

        # Mock character ownerships
        mock_character1 = Mock()
        mock_character1.character_id = 12345
        mock_character1.character_name = 'Test Character 1'

        mock_character2 = Mock()
        mock_character2.character_id = 67890
        mock_character2.character_name = 'Test Character 2'

        mock_ownership1 = Mock()
        mock_ownership1.character = mock_character1

        mock_ownership2 = Mock()
        mock_ownership2.character = mock_character2

        mock_ownerships = Mock()
        mock_ownerships.select_related.return_value.all.return_value = [
            mock_ownership1, mock_ownership2
        ]

        self.user.character_ownerships = mock_ownerships

        form = DynamicFillForm(form_obj=self.form, user=self.user)
        field_name = f'field_{char_field.pk}'

        field = form.fields[field_name]
        choice_values = [choice[1] for choice in field.choices[1:]]  # Skip empty option
        self.assertIn('Test Character 1', choice_values)
        self.assertIn('Test Character 2', choice_values)

    def test_form_validation_and_submission(self):
        """Test form validation with valid data."""
        form_data = {
            f'field_{self.text_field.pk}': 'Test answer',
            f'field_{self.number_field.pk}': '42.5',
            f'field_{self.boolean_field.pk}': 'yes',
            f'field_{self.date_field.pk}': '2023-01-15',
            f'field_{self.choice_field.pk}': 'Option 1',
            f'field_{self.multi_choice_field.pk}': ['Choice A', 'Choice B'],
        }

        form = DynamicFillForm(data=form_data, form_obj=self.form, user=self.user)
        self.assertTrue(form.is_valid())

    def test_iter_answers(self):
        """Test iterating over form answers."""
        form_data = {
            f'field_{self.text_field.pk}': 'Test answer',
            f'field_{self.number_field.pk}': '42',
            f'field_{self.boolean_field.pk}': 'yes',
        }

        form = DynamicFillForm(data=form_data, form_obj=self.form, user=self.user)
        self.assertTrue(form.is_valid())

        answers = list(form.iter_answers())
        self.assertEqual(len(answers), 6)  # All fields, even empty ones

        # Check specific answer values
        field_to_value = {field.pk: value for field, value in answers}

        self.assertEqual(field_to_value[self.text_field.pk], 'Test answer')
        self.assertEqual(field_to_value[self.number_field.pk], 42)  # Converted to int
        self.assertTrue(field_to_value[self.boolean_field.pk])

    def test_to_json_value_conversions(self):
        """Test JSON value conversions for different field types."""
        form = DynamicFillForm(form_obj=self.form, user=self.user)

        # Test number conversion
        self.assertEqual(
            form._to_json_value(self.number_field, Decimal('42')), 42
        )
        self.assertEqual(
            form._to_json_value(self.number_field, Decimal('42.5')), 42.5
        )

        # Test date conversion
        date_val = datetime.date(2023, 1, 15)
        self.assertEqual(
            form._to_json_value(self.date_field, date_val), '2023-01-15'
        )

        # Test boolean conversion
        self.assertTrue(form._to_json_value(self.boolean_field, 'yes'))
        self.assertFalse(form._to_json_value(self.boolean_field, 'no'))

        # Test multi-choice conversion
        self.assertEqual(
            form._to_json_value(self.multi_choice_field, ['Choice A', 'Choice B']),
            ['Choice A', 'Choice B']
        )

        # Test empty values
        self.assertIsNone(form._to_json_value(self.text_field, ''))
        self.assertIsNone(form._to_json_value(self.text_field, None))
        self.assertIsNone(form._to_json_value(self.multi_choice_field, []))

    def test_character_json_conversion(self):
        """Test EVE character JSON conversion."""
        char_field = FormField.objects.create(
            form=self.form,
            label='Character Question',
            field_type=FormField.FieldType.EVE_CHARACTER
        )

        form = DynamicFillForm(form_obj=self.form, user=self.user)
        form._character_names['12345'] = 'Test Character'

        result = form._to_json_value(char_field, '12345')

        expected = {
            'character_id': 12345,
            'character_name': 'Test Character'
        }
        self.assertEqual(result, expected)

    def test_form_with_no_user(self):
        """Test form creation without a user."""
        form = DynamicFillForm(form_obj=self.form, user=None)

        # Should still create fields, but character choices should be empty
        self.assertTrue(len(form.fields) > 0)
        self.assertEqual(form._character_choices, [])