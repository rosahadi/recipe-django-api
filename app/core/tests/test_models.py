import uuid
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", name="Test User", password="testpass123"
        )

    def test_create_user_successful(self):
        self.assertEqual(self.user.email, "test@example.com")
        self.assertTrue(self.user.check_password("testpass123"))
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_active)
        self.assertIsInstance(self.user.email_verification_token, uuid.UUID)
        self.assertIsNotNone(self.user.email_verification_sent_at)

    def test_is_verification_expired_true(self):
        self.user.email_verification_sent_at = timezone.now() - timedelta(hours=2)
        self.user.save()
        self.assertTrue(self.user.is_verification_expired())

    def test_is_verification_expired_false(self):
        self.user.email_verification_sent_at = timezone.now()
        self.user.save()
        self.assertFalse(self.user.is_verification_expired())

    def test_verify_email_marks_user_as_active(self):
        self.user.verify_email()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.email_verification_token)
        self.assertIsNone(self.user.email_verification_sent_at)

    def test_resend_verification_returns_false_if_not_expired(self):
        self.user.email_verification_sent_at = timezone.now()
        self.user.save()
        result = self.user.resend_verification()
        self.assertFalse(result)

    def test_resend_verification_successful_if_expired(self):
        old_token = self.user.email_verification_token
        self.user.email_verification_sent_at = timezone.now() - timedelta(hours=2)
        self.user.save()
        result = self.user.resend_verification()
        self.assertTrue(result)
        self.assertNotEqual(self.user.email_verification_token, old_token)
        self.assertAlmostEqual(
            self.user.email_verification_sent_at.timestamp(),
            timezone.now().timestamp(),
            delta=2,
        )
