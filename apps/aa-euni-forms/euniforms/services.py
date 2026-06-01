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
    def send_form_response(webhook_url, form_obj, response):
        """
        Send a form response to Discord webhook.

        Args:
            webhook_url: Discord webhook URL
            form_obj: Form model instance
            response: FormResponse model instance

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            payload = DiscordWebhookService.format_discord_message(form_obj, response)
            return DiscordWebhookService._send_webhook_request(webhook_url, payload)
        except Exception as e:
            logger.warning(
                f"Discord webhook failed for form {form_obj.pk}: {e}",
                exc_info=True
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
        # Get form answers for summary
        answers = response.answers.all()

        # Create response summary (limit to prevent Discord message limits)
        response_summary = []
        for answer in answers[:5]:  # Limit to first 5 answers
            value = answer.display_value()
            if len(value) > 100:  # Truncate long answers
                value = value[:97] + "..."
            response_summary.append(f"**{answer.field_label}**: {value}")

        if len(answers) > 5:
            response_summary.append(f"... and {len(answers) - 5} more answers")

        summary_text = "\n".join(response_summary) if response_summary else "No answers provided"

        # Format timestamp
        submitted_at = response.submitted_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Create Discord embed
        embed = {
            "title": f"New Form Response: {form_obj.title}",
            "description": "A new response has been submitted",
            "color": 3447003,  # Blue color
            "fields": [
                {
                    "name": "Submitted by",
                    "value": response.submitter_display,
                    "inline": True
                },
                {
                    "name": "Submitted at",
                    "value": submitted_at,
                    "inline": True
                },
                {
                    "name": "Form Status",
                    "value": form_obj.get_status_display(),
                    "inline": True
                },
                {
                    "name": "Response Summary",
                    "value": summary_text[:1024],  # Discord field value limit
                    "inline": False
                }
            ],
            "footer": {
                "text": "EVE University Forms"
            }
        }

        return {
            "embeds": [embed]
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