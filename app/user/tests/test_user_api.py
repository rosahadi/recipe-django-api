from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch
import uuid
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class UserAPITestCase(APITestCase):
    """Base test case setup for user API"""

    def setUp(self):
        self.client = APIClient()
        self.valid_user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }


class CreateUserViewTest(UserAPITestCase):
    """User registration tests"""

    def setUp(self):
        super().setUp()
        self.url = "/api/users/register/"

    @patch("user.views.send_verification_email")
    def test_create_user_success(self, mock_send_email):
        """Should create user and send verification email"""
        mock_send_email.return_value = True

        response = self.client.post(self.url, self.valid_user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertIn("message", response.data)

        user = User.objects.get(email="test@example.com")
        self.assertEqual(user.name, "Test User")
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.email_verification_token)

        mock_send_email.assert_called_once_with(user)

    @patch("user.views.send_verification_email")
    def test_create_user_email_send_failure(self, mock_send_email):
        """Should return 500 if verification email sending fails"""
        mock_send_email.side_effect = Exception("Email service unavailable")

        response = self.client.post(self.url, self.valid_user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(User.objects.filter(email="test@example.com").exists())

    def test_create_user_duplicate_email(self):
        """Should return 400 if email is already registered"""
        User.objects.create_user(
            email="test@example.com", name="Existing User", password="ExistingPass123!"
        )

        response = self.client.post(self.url, self.valid_user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)


class LoginViewTest(UserAPITestCase):
    """User login tests"""

    def setUp(self):
        super().setUp()
        self.url = "/api/users/login/"
        self.user = User.objects.create_user(
            email="test@example.com", name="Test User", password="TestPass123!"
        )
        self.user.is_active = True
        self.user.email_verification_token = None
        self.user.save()

        self.login_data = {"email": "test@example.com", "password": "TestPass123!"}

    def test_login_success(self):
        """Should login successfully with valid credentials"""
        response = self.client.post(self.url, self.login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "test@example.com")
        self.assertIn("message", response.data)

    def test_login_invalid_credentials(self):
        """Should return 401 for wrong password"""
        invalid_data = self.login_data.copy()
        invalid_data["password"] = "WrongPassword"

        response = self.client.post(self.url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    def test_login_unverified_user(self):
        """Should reject login if user is not verified"""
        unverified_user = User.objects.create_user(
            email="unverified@example.com",
            name="Unverified User",
            password="TestPass123!",
        )
        self.assertFalse(unverified_user.is_active)

        login_data = {"email": "unverified@example.com", "password": "TestPass123!"}
        response = self.client.post(self.url, login_data, format="json")

        self.assertIn(response.status_code,
                      [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertIn("error", response.data)

    def test_login_expired_unverified_user(self):
        """Should delete and reject login for expired unverified user"""
        expired_user = User.objects.create_user(
            email="expired@example.com", name="Expired User", password="TestPass123!"
        )
        expired_user.email_verification_sent_at = timezone.now() - timedelta(hours=2)
        expired_user.save()

        login_data = {"email": "expired@example.com", "password": "TestPass123!"}
        response = self.client.post(self.url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)


class EmailVerificationViewTest(UserAPITestCase):
    """Email verification tests"""

    def setUp(self):
        super().setUp()
        self.url = "/api/users/verify-email/"
        self.user = User.objects.create_user(
            email="test@example.com", name="Test User", password="TestPass123!"
        )
        self.user.email_verification_sent_at = timezone.now() - timedelta(minutes=30)
        self.user.save()

    def test_verify_email_success(self):
        """Should verify user with valid token"""
        data = {"token": str(self.user.email_verification_token)}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.email_verification_token)

    def test_verify_email_invalid_token(self):
        """Should return 400 for invalid token"""
        data = {"token": str(uuid.uuid4())}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


class ResendVerificationViewTest(UserAPITestCase):
    """Resend verification email tests"""

    def setUp(self):
        super().setUp()
        self.url = "/api/users/resend-verification/"

    def test_resend_verification_success_case(self):
        """Should respond with success message regardless of user existence"""
        data = {"email": "test@example.com"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_resend_verification_nonexistent_email(self):
        """Should return generic success message for non-existent email"""
        data = {"email": "nonexistent@example.com"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)


class ProfileViewTest(UserAPITestCase):
    """User profile endpoint tests"""

    def setUp(self):
        super().setUp()
        self.url = "/api/users/profile/"
        self.user = User.objects.create_user(
            email="test@example.com", name="Test User", password="TestPass123!"
        )
        self.user.is_active = True
        self.user.save()

    def test_get_profile_authenticated(self):
        """Should return profile for authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "test@example.com")

    def test_get_profile_unauthenticated(self):
        """Should reject unauthenticated access"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LogoutViewTest(UserAPITestCase):
    """Logout endpoint tests"""

    def setUp(self):
        super().setUp()
        self.url = "/api/users/logout/"
        self.user = User.objects.create_user(
            email="test@example.com", name="Test User", password="TestPass123!"
        )
        self.user.is_active = True
        self.user.save()

    def test_logout_success(self):
        """Should logout authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_logout_unauthenticated(self):
        """Should reject logout for unauthenticated user"""
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
