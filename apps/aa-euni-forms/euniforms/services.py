"""Service layer for external integrations."""

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class DiscordWebhookService:
    """Service for sending form responses to Discord webhooks."""

    @staticmethod
    def send_form_response(webhook_url, form_obj, response, retry_count=2):
        """
        Send a form response to Discord webhook with retry logic.

        Args:
            webhook_url: Discord webhook URL
            form_obj: Form model instance
            response: FormResponse model instance
            retry_count: Number of retry attempts (default: 2)

        Returns:
            bool: True if successful, False otherwise
        """
        if not webhook_url:
            logger.warning(f"No webhook URL provided for form {form_obj.pk}")
            return False

        last_exception = None
        for attempt in range(retry_count + 1):
            try:
                payload = DiscordWebhookService.format_discord_message(form_obj, response)
                success = DiscordWebhookService._send_webhook_request(webhook_url, payload)
                if success:
                    if attempt > 0:
                        logger.info(f"Discord webhook succeeded on retry {attempt} for form {form_obj.pk}")
                    return True
                else:
                    logger.warning(f"Discord webhook attempt {attempt + 1} failed for form {form_obj.pk}")
                    if attempt < retry_count:
                        # Add small delay before retry
                        import time
                        time.sleep(0.5 * (attempt + 1))  # Progressive delay

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Discord webhook attempt {attempt + 1} failed for form {form_obj.pk}: {e}"
                )
                if attempt < retry_count:
                    # Add small delay before retry
                    import time
                    time.sleep(0.5 * (attempt + 1))  # Progressive delay

        # All attempts failed
        logger.error(
            f"Discord webhook failed after {retry_count + 1} attempts for form {form_obj.pk}",
            exc_info=last_exception is not None,
            extra={
                'webhook_url': webhook_url[:50] + '...' if len(webhook_url) > 50 else webhook_url,
                'form_id': form_obj.pk,
                'response_id': response.pk
            }
        )
        return False

    @staticmethod
    def format_discord_message(form_obj, response):
        """
        Format form response data into Discord webhook payload.

        Args:
            form_obj: Form model instance
            response: FormResponse model instance

        Returns:
            dict: Discord webhook payload
        """
        # Get all form answers
        answers = response.answers.all()

        # Create clean response format without metadata
        content_lines = [form_obj.title]

        for answer in answers:
            content_lines.append(answer.field_label)
            content_lines.append(answer.display_value())

        content = "\n".join(content_lines)

        return {
            "content": content
        }

    @staticmethod
    def _send_webhook_request(webhook_url, payload):
        """
        Send HTTP POST request to Discord webhook.

        Args:
            webhook_url: Discord webhook URL
            payload: JSON payload to send

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert payload to JSON
            data = json.dumps(payload).encode('utf-8')

            # Create request
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'EVE-University-Forms/1.0'
                }
            )

            # Send request with timeout
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 204:  # Discord webhook success status
                    logger.info(f"Discord webhook sent successfully to {webhook_url[:50]}...")
                    return True
                else:
                    logger.warning(f"Discord webhook returned status {response.status}")
                    return False

        except urllib.error.HTTPError as e:
            logger.warning(f"Discord webhook HTTP error {e.code}: {e.reason}")
            return False
        except urllib.error.URLError as e:
            logger.warning(f"Discord webhook URL error: {e.reason}")
            return False
        except Exception as e:
            logger.warning(f"Discord webhook unexpected error: {e}")
            return False