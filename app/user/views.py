from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import (
    authenticate,
    login as django_login,
    get_user_model,
    logout as django_logout,
)
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
import logging

from .serializers import (
    UserCreateSerializer,
    UserSerializer,
    LoginSerializer,
    LoginResponseSerializer,
    MessageResponseSerializer,
    EmailVerificationSerializer,
    ResendVerificationSerializer,
)
from core.utils.email_utils import send_verification_email

logger = logging.getLogger(__name__)
User = get_user_model()


class CreateUserView(generics.CreateAPIView):
    """Create user and send verification email"""

    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        try:
            send_verification_email(user)
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            user.delete()
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            raise Exception("Account creation failed. Please try again later.")
        return user

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.perform_create(serializer)
            return Response(
                {
                    "message": (
                        "Account created! Check your email to verify your account."
                    ),
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    """User profile - only accessible after email verification"""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch"]

    def get_object(self):
        user = self.request.user

        if not user.is_active and user.is_verification_expired():
            logger.info(f"Deleting expired unverified user: {user.email}")
            user.delete()
            raise NotFound("Account expired. Please register again.")

        return user


@extend_schema(
    request=LoginSerializer,
    responses={
        200: LoginResponseSerializer,
        401: MessageResponseSerializer,
        403: MessageResponseSerializer,
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Login user using Django's session authentication"""

    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"]
    password = serializer.validated_data["password"]

    user = authenticate(request, username=email, password=password)

    if not user:
        logger.warning(f"Failed login attempt for email: {email}")
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )

    # Handle unverified users
    if not user.is_active:
        if user.is_verification_expired():
            logger.info(f"Deleting expired unverified user during login: {user.email}")
            user.delete()
            return Response(
                {"error": "Account expired. Please register again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(
            {
                "error": "Please verify your email first.",
                "message": "Check your email for verification link.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    django_login(request, user)
    logger.info(f"Successful login for user: {user.email}")

    return Response({"message": "Login successful", "user": UserSerializer(user).data})


@extend_schema(
    request=EmailVerificationSerializer,
    responses={
        200: MessageResponseSerializer,
        400: MessageResponseSerializer,
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    """Verify email with token"""

    serializer = EmailVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    token = serializer.validated_data["token"]

    try:
        user = User.objects.get(email_verification_token=token, is_active=False)
    except User.DoesNotExist:
        logger.warning(f"Invalid verification token attempted: {token}")
        return Response(
            {"error": "Invalid verification token."}, status=status.HTTP_400_BAD_REQUEST
        )

    if user.is_verification_expired():
        logger.info(f"Deleting expired user during verification: {user.email}")
        user.delete()
        return Response(
            {"error": "Verification link expired. Please register again."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.verify_email()
    logger.info(f"Email verified successfully for user: {user.email}")

    return Response({"message": "Email verified successfully! You can now login."})


@extend_schema(
    request=ResendVerificationSerializer, responses={200: MessageResponseSerializer}
)
@api_view(["POST"])
@permission_classes([AllowAny])
def resend_verification(request):
    """Resend verification email"""

    serializer = ResendVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"]

    try:
        user = User.objects.get(email=email, is_active=False)
    except User.DoesNotExist:
        # Don't reveal if email exists for security
        logger.info(f"Resend verification requested for non-existent email: {email}")
        return Response(
            {"message": "If the email exists, a verification link will be sent."}
        )

    if user.is_verification_expired():
        logger.info(f"Deleting expired user during resend: {user.email}")
        user.delete()
        return Response(
            {"error": "Account expired. Please register again."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user.resend_verification():
        try:
            send_verification_email(user)
            logger.info(f"Verification email resent to: {user.email}")
            return Response({"message": "Verification email sent."})
        except Exception as e:
            logger.error(
                f"Failed to resend verification email to {user.email}: {str(e)}"
            )
            return Response(
                {"error": "Failed to send verification email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        return Response({"message": "Verification email was already sent recently."})


@extend_schema(responses={200: MessageResponseSerializer})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):

    user_email = request.user.email
    django_logout(request)
    logger.info(f"User logged out: {user_email}")

    return Response({"message": "Logout successful"})
