from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.core.validators import validate_email
from django.utils import timezone
from datetime import timedelta
import uuid
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        max_length=255,
        unique=True,
        validators=[validate_email],
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)  # False until email verified
    is_staff = models.BooleanField(default=False)

    # Email verification
    email_verification_token = models.UUIDField(
        default=uuid.uuid4, null=True, blank=True
    )
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def save(self, *args, **kwargs):
        # Check if this is a new user (either no pk or force_insert=True)
        is_new = not self.pk or kwargs.get("force_insert", False)

        # Generate verification token on creation for regular users
        if is_new and not self.email_verification_token and not self.is_staff:
            self.email_verification_token = uuid.uuid4()
            self.email_verification_sent_at = timezone.now()

        super().save(*args, **kwargs)

    def is_verification_expired(self):
        """Check if verification token has expired (1 hour)"""
        if not self.email_verification_sent_at:
            return True
        return timezone.now() > self.email_verification_sent_at + timedelta(hours=1)

    def verify_email(self):
        """Mark email as verified and activate user"""
        self.is_active = True
        self.email_verification_token = None
        self.email_verification_sent_at = None
        self.save()

    def resend_verification(self):
        """Generate new verification token"""
        if not self.is_verification_expired():
            return False  # Don't resend if not expired yet

        self.email_verification_token = uuid.uuid4()
        self.email_verification_sent_at = timezone.now()
        self.save()
        return True
