"""Test cases for euniforms models."""

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
import json

from euniforms.models import Form, FormField, FieldChoice, FormResponse, FormAnswer


class FormModelTestCase(TestCase):
    """Test cases for the Form model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.group = Group.objects.create(name='Test Group')
        self.viewer_group = Group.objects.create(name='Viewer Group')

    def test_form_creation(self):
        """Test basic form creation."""
        form = Form.objects.create(
            title='Test Form',
            description='A test form',
            created_by=self.user
        )
        self.assertEqual(form.title, 'Test Form')
        self.assertEqual(form.description, 'A test form')
        self.assertEqual(form.status, Form.Status.DRAFT)
        self.assertEqual(form.created_by, self.user)
        self.assertFalse(form.allow_multiple)
        self.assertTrue(form.notify_on_submit)

    def test_form_str_representation(self):
        """Test string representation of form."""
        form = Form.objects.create(title='Test Form')
        self.assertEqual(str(form), 'Test Form')

    def test_accepts_submissions_property(self):
        """Test the accepts_submissions property."""
        form = Form.objects.create(title='Test Form', status=Form.Status.DRAFT)
        self.assertFalse(form.accepts_submissions)

        form.status = Form.Status.OPEN
        form.save()
        self.assertTrue(form.accepts_submissions)

        form.status = Form.Status.CLOSED
        form.save()
        self.assertFalse(form.accepts_submissions)

    def test_discord_webhook_validation_valid(self):
        """Test valid Discord webhook URL validation."""
        valid_urls = [
            'https://discord.com/api/webhooks/123456789/abcdefABCDEF123-456_789',
            'https://discord.com/api/webhooks/987654321/xyz789XYZ_abc-123',
        ]

        for url in valid_urls:
            form = Form(title='Test', discord_webhook_url=url)
            try:
                form.clean()  # Should not raise ValidationError
            except ValidationError:
                self.fail(f"Valid Discord webhook URL {url} raised ValidationError")

    def test_discord_webhook_validation_invalid(self):
        """Test invalid Discord webhook URL validation."""
        invalid_urls = [
            'https://example.com/webhook',
            'https://discord.com/api/webhooks/',
            'https://discord.com/api/webhooks/notanumber/token',
            'http://discord.com/api/webhooks/123/token',  # http instead of https
            'https://discord.com/api/webhooks/123/',  # missing token
        ]

        for url in invalid_urls:
            form = Form(title='Test', discord_webhook_url=url)
            with self.assertRaises(ValidationError):
                form.clean()

    def test_is_eligible_authenticated_user_no_restrictions(self):
        """Test eligibility for authenticated user with no group restrictions."""
        form = Form.objects.create(title='Test Form')
        self.assertTrue(form.is_eligible(self.user))

    def test_is_eligible_unauthenticated_user(self):
        """Test eligibility for unauthenticated user."""
        from django.contrib.auth.models import AnonymousUser
        form = Form.objects.create(title='Test Form')
        anonymous = AnonymousUser()
        self.assertFalse(form.is_eligible(anonymous))

    def test_is_eligible_restricted_group_member(self):
        """Test eligibility for user in restricted group."""
        form = Form.objects.create(title='Test Form')
        form.restricted_groups.add(self.group)

        # User not in group
        self.assertFalse(form.is_eligible(self.user))

        # User in group
        self.user.groups.add(self.group)
        self.assertTrue(form.is_eligible(self.user))

    def test_is_eligible_manager_always_eligible(self):
        """Test that users with manage_forms permission are always eligible."""
        from django.contrib.auth.models import Permission
        form = Form.objects.create(title='Test Form')
        form.restricted_groups.add(self.group)

        # Give user manage_forms permission
        manage_perm = Permission.objects.get(codename='manage_forms')
        self.user.user_permissions.add(manage_perm)

        self.assertTrue(form.is_eligible(self.user))

    def test_user_can_view_responses(self):
        """Test response viewing permissions."""
        form = Form.objects.create(title='Test Form')
        form.viewer_groups.add(self.viewer_group)

        # User not in viewer group
        self.assertFalse(form.user_can_view_responses(self.user))

        # User in viewer group
        self.user.groups.add(self.viewer_group)
        self.assertTrue(form.user_can_view_responses(self.user))

    def test_has_response_from(self):
        """Test checking if user has already responded."""
        form = Form.objects.create(title='Test Form')
        self.assertFalse(form.has_response_from(self.user))

        # Create response
        FormResponse.objects.create(form=form, user=self.user)
        self.assertTrue(form.has_response_from(self.user))

    def test_notification_recipients(self):
        """Test getting notification recipients."""
        form = Form.objects.create(title='Test Form', created_by=self.user)
        form.viewer_groups.add(self.viewer_group)

        viewer_user = User.objects.create_user(username='viewer', password='pass')
        viewer_user.groups.add(self.viewer_group)

        recipients = form.notification_recipients()
        self.assertIn(self.user, recipients)  # Creator
        self.assertIn(viewer_user, recipients)  # Viewer


class FormFieldModelTestCase(TestCase):
    """Test cases for the FormField model."""

    def setUp(self):
        """Set up test data."""
        self.form = Form.objects.create(title='Test Form')

    def test_formfield_creation(self):
        """Test basic form field creation."""
        field = FormField.objects.create(
            form=self.form,
            label='Test Field',
            field_type=FormField.FieldType.SHORT_TEXT,
            order=1
        )
        self.assertEqual(field.form, self.form)
        self.assertEqual(field.label, 'Test Field')
        self.assertEqual(field.field_type, FormField.FieldType.SHORT_TEXT)
        self.assertEqual(field.order, 1)
        self.assertTrue(field.required)

    def test_formfield_str_representation(self):
        """Test string representation of form field."""
        field = FormField.objects.create(
            form=self.form,
            label='Test Field'
        )
        self.assertEqual(str(field), 'Test Field')

    def test_is_choice_type_property(self):
        """Test the is_choice_type property."""
        # Single choice field
        single_choice = FormField.objects.create(
            form=self.form,
            label='Single Choice',
            field_type=FormField.FieldType.SINGLE_CHOICE
        )
        self.assertTrue(single_choice.is_choice_type)

        # Multi choice field
        multi_choice = FormField.objects.create(
            form=self.form,
            label='Multi Choice',
            field_type=FormField.FieldType.MULTI_CHOICE
        )
        self.assertTrue(multi_choice.is_choice_type)

        # Non-choice field
        text_field = FormField.objects.create(
            form=self.form,
            label='Text Field',
            field_type=FormField.FieldType.SHORT_TEXT
        )
        self.assertFalse(text_field.is_choice_type)

    def test_formfield_ordering(self):
        """Test form field ordering."""
        field2 = FormField.objects.create(form=self.form, label='Field 2', order=2)
        field1 = FormField.objects.create(form=self.form, label='Field 1', order=1)
        field3 = FormField.objects.create(form=self.form, label='Field 3', order=3)

        fields = list(self.form.fields.all())
        self.assertEqual(fields[0], field1)
        self.assertEqual(fields[1], field2)
        self.assertEqual(fields[2], field3)


class FieldChoiceModelTestCase(TestCase):
    """Test cases for the FieldChoice model."""

    def setUp(self):
        """Set up test data."""
        self.form = Form.objects.create(title='Test Form')
        self.field = FormField.objects.create(
            form=self.form,
            label='Choice Field',
            field_type=FormField.FieldType.SINGLE_CHOICE
        )

    def test_fieldchoice_creation(self):
        """Test basic field choice creation."""
        choice = FieldChoice.objects.create(
            field=self.field,
            value='Option 1',
            order=1
        )
        self.assertEqual(choice.field, self.field)
        self.assertEqual(choice.value, 'Option 1')
        self.assertEqual(choice.order, 1)

    def test_fieldchoice_str_representation(self):
        """Test string representation of field choice."""
        choice = FieldChoice.objects.create(
            field=self.field,
            value='Test Option'
        )
        self.assertEqual(str(choice), 'Test Option')

    def test_fieldchoice_ordering(self):
        """Test field choice ordering."""
        choice2 = FieldChoice.objects.create(field=self.field, value='Option 2', order=2)
        choice1 = FieldChoice.objects.create(field=self.field, value='Option 1', order=1)
        choice3 = FieldChoice.objects.create(field=self.field, value='Option 3', order=3)

        choices = list(self.field.choices.all())
        self.assertEqual(choices[0], choice1)
        self.assertEqual(choices[1], choice2)
        self.assertEqual(choices[2], choice3)


class FormResponseModelTestCase(TestCase):
    """Test cases for the FormResponse model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.form = Form.objects.create(title='Test Form')

    def test_formresponse_creation(self):
        """Test basic form response creation."""
        response = FormResponse.objects.create(
            form=self.form,
            user=self.user,
            main_character_id=12345,
            main_character_name='Test Character'
        )
        self.assertEqual(response.form, self.form)
        self.assertEqual(response.user, self.user)
        self.assertEqual(response.main_character_id, 12345)
        self.assertEqual(response.main_character_name, 'Test Character')

    def test_formresponse_str_representation(self):
        """Test string representation of form response."""
        response = FormResponse.objects.create(
            form=self.form,
            user=self.user,
            main_character_name='Test Character'
        )
        expected = f"{self.form.title} — Test Character"
        self.assertEqual(str(response), expected)

    def test_submitter_display_with_character(self):
        """Test submitter display with character name."""
        response = FormResponse.objects.create(
            form=self.form,
            user=self.user,
            main_character_name='Test Character'
        )
        self.assertEqual(response.submitter_display, 'Test Character')

    def test_submitter_display_with_user_only(self):
        """Test submitter display with user only."""
        response = FormResponse.objects.create(
            form=self.form,
            user=self.user
        )
        self.assertEqual(response.submitter_display, 'testuser')

    def test_submitter_display_unknown(self):
        """Test submitter display when both user and character are None."""
        response = FormResponse.objects.create(form=self.form)
        self.assertEqual(response.submitter_display, 'Unknown')


class FormAnswerModelTestCase(TestCase):
    """Test cases for the FormAnswer model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.form = Form.objects.create(title='Test Form')
        self.response = FormResponse.objects.create(form=self.form, user=self.user)
        self.field = FormField.objects.create(
            form=self.form,
            label='Test Field',
            field_type=FormField.FieldType.SHORT_TEXT
        )

    def test_formanswer_creation(self):
        """Test basic form answer creation."""
        answer = FormAnswer.objects.create(
            response=self.response,
            field=self.field,
            field_label='Test Field',
            field_type=FormField.FieldType.SHORT_TEXT,
            value='Test Answer'
        )
        self.assertEqual(answer.response, self.response)
        self.assertEqual(answer.field, self.field)
        self.assertEqual(answer.field_label, 'Test Field')
        self.assertEqual(answer.field_type, FormField.FieldType.SHORT_TEXT)
        self.assertEqual(answer.value, 'Test Answer')

    def test_formanswer_str_representation(self):
        """Test string representation of form answer."""
        answer = FormAnswer.objects.create(
            response=self.response,
            field=self.field,
            field_label='Test Field',
            field_type=FormField.FieldType.SHORT_TEXT,
            value='Test Answer'
        )
        self.assertEqual(str(answer), 'Test Field: Test Answer')

    def test_display_value_text(self):
        """Test display_value for text fields."""
        answer = FormAnswer.objects.create(
            response=self.response,
            field=self.field,
            field_label='Text Field',
            field_type=FormField.FieldType.SHORT_TEXT,
            value='Hello World'
        )
        self.assertEqual(answer.display_value(), 'Hello World')

    def test_display_value_boolean_true(self):
        """Test display_value for boolean field (True)."""
        answer = FormAnswer.objects.create(
            response=self.response,
            field=self.field,
            field_label='Boolean Field',
            field_type=FormField.FieldType.BOOLEAN,
            value=True
        )
        self.assertEqual(answer.display_value(), 'Yes')

    def test_display_value_boolean_false(self):
        """Test display_value for boolean field (False)."""
        answer = FormAnswer.objects.create(
            response=self.response,
            field=self.field,
            field_label='Boolean Field',
            field_type=FormField.FieldType.BOOLEAN,
            value=False
        )
        self.assertEqual(answer.display_value(), 'No')

    def test_display_value_multi_choice(self):
        """Test display_value for multi-choice field."""
        answer = FormAnswer.objects.create(
            response=self.response,
            field=self.field,
            field_label='Multi Choice',
            field_type=FormField.FieldType.MULTI_CHOICE,
            value=['Option 1', 'Option 2', 'Option 3']
        )
        self.assertEqual(answer.display_value(), 'Option 1, Option 2, Option 3')

    def test_display_value_eve_character(self):
        """Test display_value for EVE character field."""
        character_data = {
            'character_id': 12345,
            'character_name': 'Test Character'
        }
        answer = FormAnswer.objects.create(
            response=self.response,
            field=self.field,
            field_label='Character Field',
            field_type=FormField.FieldType.EVE_CHARACTER,
            value=character_data
        )
        self.assertEqual(answer.display_value(), 'Test Character')

    def test_display_value_empty(self):
        """Test display_value for empty values."""
        test_cases = [None, '', []]
        for empty_value in test_cases:
            answer = FormAnswer.objects.create(
                response=self.response,
                field=self.field,
                field_label='Empty Field',
                field_type=FormField.FieldType.SHORT_TEXT,
                value=empty_value
            )
            self.assertEqual(answer.display_value(), '')