"""Test cases for euniforms services."""

from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import Mock, patch, MagicMock
import json
import urllib.error

from euniforms.models import Form, FormField, FormResponse, FormAnswer
from euniforms.services import DiscordWebhookService


class DiscordWebhookServiceTestCase(TestCase):
    """Test cases for the Discord webhook service."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.form = Form.objects.create(
            title='Test Form',
            description='A test form',
            status=Form.Status.OPEN,
            created_by=self.user
        )

        # Create form fields
        self.field1 = FormField.objects.create(
            form=self.form,
            label='Short Question',
            field_type=FormField.FieldType.SHORT_TEXT,
            order=1
        )
        self.field2 = FormField.objects.create(
            form=self.form,
            label='Boolean Question',
            field_type=FormField.FieldType.BOOLEAN,
            order=2
        )

        # Create response
        self.response = FormResponse.objects.create(
            form=self.form,
            user=self.user,
            main_character_id=12345,
            main_character_name='Test Character'
        )

        # Create answers
        self.answer1 = FormAnswer.objects.create(
            response=self.response,
            field=self.field1,
            field_label=self.field1.label,
            field_type=self.field1.field_type,
            value='Short answer text'
        )
        self.answer2 = FormAnswer.objects.create(
            response=self.response,
            field=self.field2,
            field_label=self.field2.label,
            field_type=self.field2.field_type,
            value=True
        )

        self.webhook_url = 'https://discord.com/api/webhooks/123456789/test-token'

    def test_format_discord_message_basic(self):
        """Test basic Discord message formatting."""
        payload = DiscordWebhookService.format_discord_message(self.form, self.response)

        self.assertIn('embeds', payload)
        embed = payload['embeds'][0]

        # Check embed structure
        self.assertEqual(embed['title'], 'New Form Response: Test Form')
        self.assertEqual(embed['description'], 'A new response has been submitted')
        self.assertEqual(embed['color'], 3447003)

        # Check fields
        fields = embed['fields']
        field_names = [field['name'] for field in fields]

        self.assertIn('Submitted by', field_names)
        self.assertIn('Submitted at', field_names)
        self.assertIn('Form Status', field_names)
        self.assertIn('Response Summary', field_names)

    def test_format_discord_message_submitter_display(self):
        """Test submitter display in Discord message."""
        payload = DiscordWebhookService.format_discord_message(self.form, self.response)
        embed = payload['embeds'][0]

        # Find submitter field
        submitter_field = next(
            field for field in embed['fields']
            if field['name'] == 'Submitted by'
        )
        self.assertEqual(submitter_field['value'], 'Test Character')

    def test_format_discord_message_response_summary(self):
        """Test response summary formatting."""
        payload = DiscordWebhookService.format_discord_message(self.form, self.response)
        embed = payload['embeds'][0]

        # Find response summary field
        summary_field = next(
            field for field in embed['fields']
            if field['name'] == 'Response Summary'
        )

        summary_value = summary_field['value']
        self.assertIn('**Short Question**: Short answer text', summary_value)
        self.assertIn('**Boolean Question**: Yes', summary_value)

    def test_format_discord_message_long_answer_truncation(self):
        """Test that long answers are properly truncated."""
        # Create a long answer
        long_text = 'A' * 150  # Longer than 100 char limit
        long_answer = FormAnswer.objects.create(
            response=self.response,
            field=FormField.objects.create(
                form=self.form,
                label='Long Question',
                field_type=FormField.FieldType.LONG_TEXT,
                order=3
            ),
            field_label='Long Question',
            field_type=FormField.FieldType.LONG_TEXT,
            value=long_text
        )

        payload = DiscordWebhookService.format_discord_message(self.form, self.response)
        embed = payload['embeds'][0]

        summary_field = next(
            field for field in embed['fields']
            if field['name'] == 'Response Summary'
        )

        # Check that long answer is truncated
        self.assertIn('A' * 97 + '...', summary_field['value'])

    def test_format_discord_message_many_answers_limit(self):
        """Test that responses with many answers are limited to first 5."""
        # Create more fields and answers (total will be 7)
        for i in range(3, 8):
            field = FormField.objects.create(
                form=self.form,
                label=f'Question {i}',
                field_type=FormField.FieldType.SHORT_TEXT,
                order=i
            )
            FormAnswer.objects.create(
                response=self.response,
                field=field,
                field_label=f'Question {i}',
                field_type=FormField.FieldType.SHORT_TEXT,
                value=f'Answer {i}'
            )

        payload = DiscordWebhookService.format_discord_message(self.form, self.response)
        embed = payload['embeds'][0]

        summary_field = next(
            field for field in embed['fields']
            if field['name'] == 'Response Summary'
        )

        # Should indicate more answers exist
        self.assertIn('... and 2 more answers', summary_field['value'])

    def test_format_discord_message_no_answers(self):
        """Test message formatting when no answers exist."""
        # Create response with no answers
        empty_response = FormResponse.objects.create(
            form=self.form,
            user=self.user,
            main_character_name='Empty Character'
        )

        payload = DiscordWebhookService.format_discord_message(self.form, empty_response)
        embed = payload['embeds'][0]

        summary_field = next(
            field for field in embed['fields']
            if field['name'] == 'Response Summary'
        )

        self.assertEqual(summary_field['value'], 'No answers provided')

    def test_format_discord_message_summary_length_limit(self):
        """Test that summary is limited to Discord field limit."""
        # Create a response with very long summary
        long_form = Form.objects.create(title='Very Long Form')
        long_response = FormResponse.objects.create(
            form=long_form,
            user=self.user,
            main_character_name='Test'
        )

        # Create field with very long value
        field = FormField.objects.create(
            form=long_form,
            label='A' * 50,  # Long label
            field_type=FormField.FieldType.LONG_TEXT
        )
        FormAnswer.objects.create(
            response=long_response,
            field=field,
            field_label='A' * 50,
            field_type=FormField.FieldType.LONG_TEXT,
            value='B' * 1000  # Very long value
        )

        payload = DiscordWebhookService.format_discord_message(long_form, long_response)
        embed = payload['embeds'][0]

        summary_field = next(
            field for field in embed['fields']
            if field['name'] == 'Response Summary'
        )

        # Should be limited to 1024 characters
        self.assertLessEqual(len(summary_field['value']), 1024)

    @patch('urllib.request.urlopen')
    def test_send_webhook_request_success(self, mock_urlopen):
        """Test successful webhook request."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__.return_value = mock_response

        mock_urlopen.return_value = mock_response

        payload = {'test': 'data'}
        result = DiscordWebhookService._send_webhook_request(self.webhook_url, payload)

        self.assertTrue(result)
        mock_urlopen.assert_called_once()

        # Check request was created correctly
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        self.assertEqual(request.get_full_url(), self.webhook_url)
        self.assertEqual(request.headers['Content-type'], 'application/json')
        self.assertEqual(request.headers['User-agent'], 'EVE-University-Forms/1.0')

    @patch('urllib.request.urlopen')
    def test_send_webhook_request_wrong_status(self, mock_urlopen):
        """Test webhook request with wrong status code."""
        mock_response = MagicMock()
        mock_response.status = 400  # Bad request
        mock_response.__enter__.return_value = mock_response

        mock_urlopen.return_value = mock_response

        payload = {'test': 'data'}
        result = DiscordWebhookService._send_webhook_request(self.webhook_url, payload)

        self.assertFalse(result)

    @patch('urllib.request.urlopen')
    def test_send_webhook_request_http_error(self, mock_urlopen):
        """Test webhook request with HTTP error."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url=self.webhook_url,
            code=404,
            msg='Not Found',
            hdrs={},
            fp=None
        )

        payload = {'test': 'data'}
        result = DiscordWebhookService._send_webhook_request(self.webhook_url, payload)

        self.assertFalse(result)

    @patch('urllib.request.urlopen')
    def test_send_webhook_request_url_error(self, mock_urlopen):
        """Test webhook request with URL error."""
        mock_urlopen.side_effect = urllib.error.URLError('Connection failed')

        payload = {'test': 'data'}
        result = DiscordWebhookService._send_webhook_request(self.webhook_url, payload)

        self.assertFalse(result)

    @patch('urllib.request.urlopen')
    def test_send_webhook_request_timeout(self, mock_urlopen):
        """Test webhook request timeout."""
        import socket
        mock_urlopen.side_effect = socket.timeout('Request timed out')

        payload = {'test': 'data'}
        result = DiscordWebhookService._send_webhook_request(self.webhook_url, payload)

        self.assertFalse(result)

    @patch.object(DiscordWebhookService, '_send_webhook_request')
    def test_send_form_response_success(self, mock_send):
        """Test successful form response sending."""
        mock_send.return_value = True

        result = DiscordWebhookService.send_form_response(
            self.webhook_url, self.form, self.response
        )

        self.assertTrue(result)
        mock_send.assert_called_once()

        # Verify payload was formatted correctly
        args, kwargs = mock_send.call_args
        webhook_url, payload = args
        self.assertEqual(webhook_url, self.webhook_url)
        self.assertIn('embeds', payload)

    @patch.object(DiscordWebhookService, '_send_webhook_request')
    def test_send_form_response_failure(self, mock_send):
        """Test form response sending failure."""
        mock_send.return_value = False

        result = DiscordWebhookService.send_form_response(
            self.webhook_url, self.form, self.response
        )

        self.assertFalse(result)

    @patch.object(DiscordWebhookService, 'format_discord_message')
    def test_send_form_response_exception_handling(self, mock_format):
        """Test exception handling in send_form_response."""
        mock_format.side_effect = Exception('Formatting error')

        with patch('euniforms.services.logger.warning') as mock_logger:
            result = DiscordWebhookService.send_form_response(
                self.webhook_url, self.form, self.response
            )

            self.assertFalse(result)
            mock_logger.assert_called_once()

    def test_webhook_request_payload_encoding(self):
        """Test that payload is properly JSON encoded."""
        payload = {
            'test': 'data',
            'unicode': 'üñíčødé',
            'number': 123
        }

        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            DiscordWebhookService._send_webhook_request(self.webhook_url, payload)

            # Check that data was properly encoded
            args, kwargs = mock_urlopen.call_args
            request = args[0]
            data = request.data

            # Should be valid JSON bytes
            decoded = json.loads(data.decode('utf-8'))
            self.assertEqual(decoded['test'], 'data')
            self.assertEqual(decoded['unicode'], 'üñíčødé')
            self.assertEqual(decoded['number'], 123)