"""Test cases for euniforms views."""

from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.http import Http404
from unittest.mock import Mock, patch
import json

from euniforms.models import Form, FormField, FieldChoice, FormResponse, FormAnswer


class BaseViewTestCase(TestCase):
    """Base test case with common setup for view tests."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create users
        self.regular_user = User.objects.create_user(
            username='regular', password='testpass'
        )
        self.manager_user = User.objects.create_user(
            username='manager', password='testpass'
        )

        # Create groups
        self.restricted_group = Group.objects.create(name='Restricted')
        self.viewer_group = Group.objects.create(name='Viewers')

        # Add permissions
        basic_access = Permission.objects.get(codename='basic_access')
        manage_forms = Permission.objects.get(codename='manage_forms')

        self.regular_user.user_permissions.add(basic_access)
        self.manager_user.user_permissions.add(basic_access, manage_forms)

        # Add users to groups
        self.regular_user.groups.add(self.restricted_group)

        # Create test form
        self.form = Form.objects.create(
            title='Test Form',
            description='A test form',
            status=Form.Status.OPEN,
            created_by=self.manager_user
        )
        self.form.restricted_groups.add(self.restricted_group)
        self.form.viewer_groups.add(self.viewer_group)

        # Create form field
        self.field = FormField.objects.create(
            form=self.form,
            label='Test Question',
            field_type=FormField.FieldType.SHORT_TEXT,
            order=1
        )

    def create_mock_main_character(self, user):
        """Create a mock main character for testing."""
        mock_character = Mock()
        mock_character.character_id = 12345
        mock_character.character_name = 'Test Character'

        mock_profile = Mock()
        mock_profile.main_character = mock_character
        user.profile = mock_profile

        return mock_character


class IndexViewTestCase(BaseViewTestCase):
    """Test cases for the index view."""

    def test_index_requires_login(self):
        """Test that index view requires login."""
        response = self.client.get(reverse('euniforms:index'))
        self.assertRedirects(response, '/accounts/login/?next=/euniforms/')

    def test_index_requires_app_access(self):
        """Test that index view requires app access."""
        user_no_access = User.objects.create_user(
            username='noaccess', password='testpass'
        )
        self.client.force_login(user_no_access)

        response = self.client.get(reverse('euniforms:index'))
        self.assertEqual(response.status_code, 403)

    def test_index_regular_user(self):
        """Test index view for regular user."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('euniforms:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Form')
        self.assertIn('fillable_forms', response.context)
        self.assertEqual(response.context['can_manage'], False)

    def test_index_manager_user(self):
        """Test index view for manager user."""
        self.client.force_login(self.manager_user)
        response = self.client.get(reverse('euniforms:index'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['can_manage'], True)
        self.assertTrue(len(response.context['managed_forms']) > 0)

    def test_index_search_functionality(self):
        """Test search functionality in index view."""
        self.client.force_login(self.regular_user)

        # Create another form
        Form.objects.create(
            title='Another Form',
            description='Different form',
            status=Form.Status.OPEN
        )

        # Search for specific form
        response = self.client.get(reverse('euniforms:index'), {'search': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Form')

    def test_index_eligibility_filtering(self):
        """Test that only eligible forms are shown to users."""
        # Create form with different restriction
        other_group = Group.objects.create(name='Other')
        restricted_form = Form.objects.create(
            title='Restricted Form',
            status=Form.Status.OPEN
        )
        restricted_form.restricted_groups.add(other_group)

        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('euniforms:index'))

        # Should see eligible form, not restricted form
        self.assertContains(response, 'Test Form')
        self.assertNotContains(response, 'Restricted Form')


class FormFillViewTestCase(BaseViewTestCase):
    """Test cases for the form fill view."""

    def test_form_fill_requires_login(self):
        """Test that form fill requires login."""
        response = self.client.get(
            reverse('euniforms:form_fill', kwargs={'form_pk': self.form.pk})
        )
        expected_url = f'/accounts/login/?next=/euniforms/fill/{self.form.pk}/'
        self.assertRedirects(response, expected_url)

    def test_form_fill_requires_eligibility(self):
        """Test that form fill requires user eligibility."""
        # Create user not in restricted group
        non_eligible_user = User.objects.create_user(
            username='noneligible', password='testpass'
        )
        basic_access = Permission.objects.get(codename='basic_access')
        non_eligible_user.user_permissions.add(basic_access)

        self.client.force_login(non_eligible_user)
        response = self.client.get(
            reverse('euniforms:form_fill', kwargs={'form_pk': self.form.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_form_fill_draft_access(self):
        """Test that draft forms are only accessible to managers."""
        self.form.status = Form.Status.DRAFT
        self.form.save()

        # Regular user should get 404
        self.client.force_login(self.regular_user)
        response = self.client.get(
            reverse('euniforms:form_fill', kwargs={'form_pk': self.form.pk})
        )
        self.assertEqual(response.status_code, 404)

        # Manager should access successfully
        self.client.force_login(self.manager_user)
        response = self.client.get(
            reverse('euniforms:form_fill', kwargs={'form_pk': self.form.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_form_fill_closed_form_blocked(self):
        """Test that closed forms show blocked message."""
        self.form.status = Form.Status.CLOSED
        self.form.save()

        self.client.force_login(self.regular_user)
        response = self.client.get(
            reverse('euniforms:form_fill', kwargs={'form_pk': self.form.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'closed and no longer accepting')
        self.assertIsNotNone(response.context['blocked_reason'])

    def test_form_fill_already_submitted_blocked(self):
        """Test that already submitted forms show blocked message."""
        # Create existing response
        FormResponse.objects.create(
            form=self.form,
            user=self.regular_user,
            main_character_id=12345,
            main_character_name='Test Character'
        )

        self.client.force_login(self.regular_user)
        response = self.client.get(
            reverse('euniforms:form_fill', kwargs={'form_pk': self.form.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already submitted')
        self.assertIsNotNone(response.context['blocked_reason'])

    @patch('euniforms.views._main_character')
    @patch('euniforms.views._save_response')
    def test_form_fill_successful_submission(self, mock_save, mock_main_char):
        """Test successful form submission."""
        # Setup mocks
        mock_character = self.create_mock_main_character(self.regular_user)
        mock_main_char.return_value = mock_character
        mock_save.return_value = Mock()

        self.client.force_login(self.regular_user)

        # Submit form
        post_data = {f'field_{self.field.pk}': 'Test Answer'}
        response = self.client.post(
            reverse('euniforms:form_fill', kwargs={'form_pk': self.form.pk}),
            post_data
        )

        # Should redirect to submitted page
        expected_url = reverse('euniforms:form_submitted', kwargs={'form_pk': self.form.pk})
        self.assertRedirects(response, expected_url)
        mock_save.assert_called_once()

    @patch('euniforms.views._main_character')
    def test_form_fill_no_main_character(self, mock_main_char):
        """Test form submission without main character."""
        mock_main_char.return_value = None

        self.client.force_login(self.regular_user)

        post_data = {f'field_{self.field.pk}': 'Test Answer'}
        response = self.client.post(
            reverse('euniforms:form_fill', kwargs={'form_pk': self.form.pk}),
            post_data
        )

        self.assertEqual(response.status_code, 200)
        # Should show error message
        messages = list(response.context['messages'])
        self.assertTrue(any('main character' in str(m) for m in messages))


class FormManagementViewTestCase(BaseViewTestCase):
    """Test cases for form management views."""

    def test_form_create_requires_permission(self):
        """Test that form creation requires manage_forms permission."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('euniforms:form_create'))
        self.assertEqual(response.status_code, 403)

    def test_form_create_get(self):
        """Test form creation GET request."""
        self.client.force_login(self.manager_user)
        response = self.client.get(reverse('euniforms:form_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Form')

    def test_form_create_post_success(self):
        """Test successful form creation."""
        self.client.force_login(self.manager_user)

        post_data = {
            'title': 'New Test Form',
            'description': 'A new form for testing',
            'status': Form.Status.DRAFT,
            'allow_multiple': False,
            'notify_on_submit': True,
        }
        response = self.client.post(reverse('euniforms:form_create'), post_data)

        # Should redirect to field management
        new_form = Form.objects.get(title='New Test Form')
        expected_url = reverse('euniforms:manage_fields', kwargs={'form_pk': new_form.pk})
        self.assertRedirects(response, expected_url)

        # Verify form was created with correct user
        self.assertEqual(new_form.created_by, self.manager_user)

    def test_form_edit_get(self):
        """Test form edit GET request."""
        self.client.force_login(self.manager_user)
        response = self.client.get(
            reverse('euniforms:form_edit', kwargs={'form_pk': self.form.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Form')
        self.assertEqual(response.context['form'].instance, self.form)

    def test_form_edit_post_success(self):
        """Test successful form edit."""
        self.client.force_login(self.manager_user)

        post_data = {
            'title': 'Updated Form Title',
            'description': self.form.description,
            'status': self.form.status,
            'allow_multiple': self.form.allow_multiple,
            'notify_on_submit': self.form.notify_on_submit,
        }
        response = self.client.post(
            reverse('euniforms:form_edit', kwargs={'form_pk': self.form.pk}),
            post_data
        )

        expected_url = reverse('euniforms:manage_fields', kwargs={'form_pk': self.form.pk})
        self.assertRedirects(response, expected_url)

        # Verify form was updated
        self.form.refresh_from_db()
        self.assertEqual(self.form.title, 'Updated Form Title')

    def test_form_delete_get(self):
        """Test form delete confirmation page."""
        self.client.force_login(self.manager_user)
        response = self.client.get(
            reverse('euniforms:form_delete', kwargs={'form_pk': self.form.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Form')

    def test_form_delete_post(self):
        """Test form deletion."""
        self.client.force_login(self.manager_user)
        form_pk = self.form.pk

        response = self.client.post(
            reverse('euniforms:form_delete', kwargs={'form_pk': form_pk})
        )

        self.assertRedirects(response, reverse('euniforms:index'))
        self.assertFalse(Form.objects.filter(pk=form_pk).exists())


class FieldManagementViewTestCase(BaseViewTestCase):
    """Test cases for field management views."""

    def test_field_create_success(self):
        """Test successful field creation."""
        self.client.force_login(self.manager_user)

        post_data = {
            'label': 'New Question',
            'field_type': FormField.FieldType.LONG_TEXT,
            'required': True,
            'help_text': 'Help text for question',
        }
        response = self.client.post(
            reverse('euniforms:field_create', kwargs={'form_pk': self.form.pk}),
            post_data
        )

        expected_url = reverse('euniforms:manage_fields', kwargs={'form_pk': self.form.pk})
        self.assertRedirects(response, expected_url)

        # Verify field was created
        self.assertTrue(FormField.objects.filter(
            form=self.form, label='New Question'
        ).exists())

    def test_field_edit_success(self):
        """Test successful field edit."""
        self.client.force_login(self.manager_user)

        post_data = {
            'label': 'Updated Question',
            'field_type': self.field.field_type,
            'required': self.field.required,
            'help_text': 'Updated help text',
        }
        response = self.client.post(
            reverse('euniforms:field_edit', kwargs={'field_pk': self.field.pk}),
            post_data
        )

        expected_url = reverse('euniforms:manage_fields', kwargs={'form_pk': self.form.pk})
        self.assertRedirects(response, expected_url)

        # Verify field was updated
        self.field.refresh_from_db()
        self.assertEqual(self.field.label, 'Updated Question')

    def test_field_delete_success(self):
        """Test successful field deletion."""
        self.client.force_login(self.manager_user)
        field_pk = self.field.pk

        response = self.client.post(
            reverse('euniforms:field_delete', kwargs={'field_pk': field_pk})
        )

        expected_url = reverse('euniforms:manage_fields', kwargs={'form_pk': self.form.pk})
        self.assertRedirects(response, expected_url)

        # Verify field was deleted
        self.assertFalse(FormField.objects.filter(pk=field_pk).exists())

    def test_field_move_up(self):
        """Test moving field up in order."""
        # Create second field
        field2 = FormField.objects.create(
            form=self.form,
            label='Second Question',
            field_type=FormField.FieldType.SHORT_TEXT,
            order=2
        )

        self.client.force_login(self.manager_user)
        response = self.client.post(
            reverse('euniforms:field_move', kwargs={
                'field_pk': field2.pk, 'direction': 'up'
            })
        )

        expected_url = reverse('euniforms:manage_fields', kwargs={'form_pk': self.form.pk})
        self.assertRedirects(response, expected_url)

        # Verify order changed
        field2.refresh_from_db()
        self.field.refresh_from_db()
        self.assertEqual(field2.order, 1)
        self.assertEqual(self.field.order, 2)


class ResponseViewTestCase(BaseViewTestCase):
    """Test cases for response viewing views."""

    def setUp(self):
        """Additional setup for response tests."""
        super().setUp()

        # Create test response
        self.response = FormResponse.objects.create(
            form=self.form,
            user=self.regular_user,
            main_character_id=12345,
            main_character_name='Test Character'
        )

        # Create test answer
        self.answer = FormAnswer.objects.create(
            response=self.response,
            field=self.field,
            field_label=self.field.label,
            field_type=self.field.field_type,
            value='Test Answer'
        )

    def test_responses_list_requires_permission(self):
        """Test that responses list requires appropriate permissions."""
        # Regular user without viewer permission
        self.client.force_login(self.regular_user)
        response = self.client.get(
            reverse('euniforms:responses_list', kwargs={'form_pk': self.form.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_responses_list_viewer_access(self):
        """Test that viewer group members can access responses."""
        self.regular_user.groups.add(self.viewer_group)
        self.client.force_login(self.regular_user)

        response = self.client.get(
            reverse('euniforms:responses_list', kwargs={'form_pk': self.form.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_responses_list_manager_access(self):
        """Test that managers can always access responses."""
        self.client.force_login(self.manager_user)

        response = self.client.get(
            reverse('euniforms:responses_list', kwargs={'form_pk': self.form.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Character')

    def test_response_detail_access(self):
        """Test response detail view access."""
        self.client.force_login(self.manager_user)

        response = self.client.get(
            reverse('euniforms:response_detail', kwargs={'response_pk': self.response.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Answer')

    def test_responses_csv_export(self):
        """Test CSV export functionality."""
        self.client.force_login(self.manager_user)

        response = self.client.get(
            reverse('euniforms:responses_csv', kwargs={'form_pk': self.form.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="test-form-responses.csv"',
                     response['Content-Disposition'])

    def test_responses_list_search(self):
        """Test search functionality in responses list."""
        self.client.force_login(self.manager_user)

        # Test search by submitter name
        response = self.client.get(
            reverse('euniforms:responses_list', kwargs={'form_pk': self.form.pk}),
            {'search': 'Test Character'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Character')

    def test_responses_list_date_filtering(self):
        """Test date filtering in responses list."""
        self.client.force_login(self.manager_user)

        # Test date range filtering
        import datetime
        today = datetime.date.today()
        response = self.client.get(
            reverse('euniforms:responses_list', kwargs={'form_pk': self.form.pk}),
            {
                'start_date': today.strftime('%Y-%m-%d'),
                'end_date': today.strftime('%Y-%m-%d')
            }
        )

        self.assertEqual(response.status_code, 200)


class UtilityFunctionTestCase(BaseViewTestCase):
    """Test cases for utility functions."""

    def test_has_app_access_basic(self):
        """Test _has_app_access with basic permission."""
        from euniforms.views import _has_app_access
        self.assertTrue(_has_app_access(self.regular_user))

    def test_has_app_access_manage(self):
        """Test _has_app_access with manage permission."""
        from euniforms.views import _has_app_access
        self.assertTrue(_has_app_access(self.manager_user))

    def test_has_app_access_none(self):
        """Test _has_app_access with no permissions."""
        from euniforms.views import _has_app_access
        user_no_perms = User.objects.create_user(
            username='noperms', password='testpass'
        )
        self.assertFalse(_has_app_access(user_no_perms))

    def test_main_character_exists(self):
        """Test _main_character when character exists."""
        from euniforms.views import _main_character
        mock_char = self.create_mock_main_character(self.regular_user)
        result = _main_character(self.regular_user)
        self.assertEqual(result, mock_char)

    def test_main_character_no_profile(self):
        """Test _main_character when no profile exists."""
        from euniforms.views import _main_character
        user_no_profile = User.objects.create_user(
            username='noprofile', password='testpass'
        )
        result = _main_character(user_no_profile)
        self.assertIsNone(result)