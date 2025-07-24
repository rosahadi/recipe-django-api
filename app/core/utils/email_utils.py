from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_verification_email(user):
    """Send email verification link to user"""

    try:
        verification_url = (
            f"{settings.FRONTEND_URL}/verify-email/{user.email_verification_token}"
        )

        html_content, text_content = get_verification_email_content(
            user.name, verification_url
        )

        email = EmailMultiAlternatives(
            subject="Verify Your Email Address",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")

        sent = email.send()

        if sent:
            logger.info(f"Verification email sent to {user.email}")
            return True
        else:
            logger.error(f"Failed to send verification email to {user.email}")
            return False

    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False


def get_verification_email_content(user_name, verification_url):
    """Get HTML and text content for verification email"""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif;
                        max-width: 600px; margin: 0 auto; padding: 20px; }}
            .container {{ background: white; padding: 30px;
                            border-radius: 8px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .button {{ display: inline-block; background: #007bff;
                        color: white; padding: 12px 24px;
                        text-decoration: none; border-radius: 4px; margin: 20px 0; }}
            .footer {{ margin-top: 30px; font-size: 14px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Verify Your Email</h1>
            <p>Hi {user_name},</p>
            <p>Click the button below to verify your email address:</p>
            <a href="{verification_url}" class="button">Verify Email</a>
            <p>Or copy this link: <br>{verification_url}</p>
            <p><strong>This link expires in 1 hour.</strong></p>
            <div class="footer">
                <p>If you didn't sign up, please ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Hi {user_name},

    Please verify your email by clicking this link:
    {verification_url}

    This link expires in 1 hour.

    If you didn't sign up, please ignore this email.
    """

    return html_content, text_content
