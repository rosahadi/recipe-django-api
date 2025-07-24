from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""

    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ["email", "name", "password", "password_confirm"]

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("Email already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords don't match."})

        # Validate password strength
        try:
            validate_password(attrs["password"])
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})

        attrs.pop("password_confirm")
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""

    class Meta:
        model = User
        fields = ["id", "email", "name", "is_active"]
        read_only_fields = ["id", "is_active"]


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True, write_only=True, style={"input_type": "password"}
    )


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""

    token = serializers.UUIDField(required=True)


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending verification"""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.lower()


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response"""

    message = serializers.CharField()
    user = UserSerializer()


class MessageResponseSerializer(serializers.Serializer):
    """Serializer for simple message responses"""

    message = serializers.CharField()
