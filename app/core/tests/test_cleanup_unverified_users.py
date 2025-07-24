from django.core.management import call_command
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth import get_user_model
from io import StringIO
import datetime

User = get_user_model()


class CleanupUnverifiedUsersCommandTests(TestCase):
    def setUp(self):
        now = timezone.now()

        # Unverified, expired (should be deleted)
        self.expired_user = User.objects.create(
            email="expired@example.com",
            is_active=False,
            email_verification_sent_at=now - datetime.timedelta(hours=2),
        )

        # Unverified, not expired (should not be deleted)
        self.recent_user = User.objects.create(
            email="recent@example.com",
            is_active=False,
            email_verification_sent_at=now - datetime.timedelta(minutes=30),
        )

        # Verified user (should not be deleted)
        self.verified_user = User.objects.create(
            email="verified@example.com",
            is_active=True,
            email_verification_sent_at=now - datetime.timedelta(hours=3),
        )

    def test_cleanup_command_deletes_only_expired_unverified_users(self):
        out = StringIO()
        call_command("clean_expired_unverified_users", stdout=out)

        # Check that only the expired unverified user was deleted
        self.assertFalse(User.objects.filter(email="expired@example.com").exists())
        self.assertTrue(User.objects.filter(email="recent@example.com").exists())
        self.assertTrue(User.objects.filter(email="verified@example.com").exists())

        output = out.getvalue()
        self.assertIn("Successfully deleted 1 expired unverified users", output)
