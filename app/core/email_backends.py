import logging
import resend
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """Custom email backend for Resend API integration."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        resend.api_key = settings.RESEND_API_KEY

    def send_messages(self, email_messages):
        """Send one or more EmailMessage objects and return the number sent."""
        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            try:
                if self._send_message(message):
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                if not self.fail_silently:
                    raise

        return sent_count

    def _send_message(self, message):
        """Send a single EmailMessage object."""
        try:
            email_data = {
                "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                "to": message.to,
                "subject": message.subject,
            }

            # Add CC and BCC if present
            if message.cc:
                email_data["cc"] = message.cc
            if message.bcc:
                email_data["bcc"] = message.bcc

            # Handle HTML and text content
            if isinstance(message, EmailMultiAlternatives):
                html_content = None
                for content, mimetype in message.alternatives:
                    if mimetype == "text/html":
                        html_content = content
                        break

                if html_content:
                    email_data["html"] = html_content
                    if message.body:
                        email_data["text"] = message.body
                else:
                    email_data["text"] = message.body
            else:
                email_data["text"] = message.body

            response = resend.Emails.send(email_data)

            if response.get("id"):
                logger.info(f"Email sent successfully. ID: {response['id']}")
                return True
            else:
                logger.error(f"Failed to send email: {response}")
                return False

        except Exception as e:
            logger.error(f"Error sending email via Resend: {str(e)}")
            if not self.fail_silently:
                raise
            return False
