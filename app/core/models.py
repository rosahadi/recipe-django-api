from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.conf import settings
from django.core.validators import validate_email, MinValueValidator
from django.utils import timezone
from datetime import timedelta
import uuid
import os
from .managers import UserManager


def recipe_image_file_path(instance, filename):
    """Generate file path for new recipe image."""
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("uploads", "recipe", filename)


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
        return timezone.now() > self.email_verification_sent_at + timedelta(
            hours=1
        )

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


class TimeStampedModel(models.Model):
    """Abstract base model with created and modified timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tag(TimeStampedModel):
    """Global tags shared across all recipes."""

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)

    # Track usage to prevent deletion of popular tags
    usage_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

    def increment_usage(self):
        """Increment usage count when tag is used"""
        self.usage_count += 1
        self.save(update_fields=["usage_count"])

    def decrement_usage(self):
        """Decrement usage count when tag is removed"""
        if self.usage_count > 0:
            self.usage_count -= 1
            self.save(update_fields=["usage_count"])


class Ingredient(TimeStampedModel):
    """Global ingredients shared across all recipes."""

    name = models.CharField(max_length=255, unique=True)

    # Optional category for better organization
    category = models.CharField(max_length=100, blank=True)

    # Track usage
    usage_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

    def increment_usage(self):
        """Increment usage count when ingredient is used"""
        self.usage_count += 1
        self.save(update_fields=["usage_count"])

    def decrement_usage(self):
        """Decrement usage count when ingredient is removed"""
        if self.usage_count > 0:
            self.usage_count -= 1
            self.save(update_fields=["usage_count"])


class Recipe(TimeStampedModel):
    """Recipe object."""

    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    # Basic Information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField()

    # Time and Difficulty
    time_minutes = models.IntegerField(validators=[MinValueValidator(1)])
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, default="easy"
    )

    # Servings
    servings = models.IntegerField(validators=[MinValueValidator(1)], default=4)

    # Relationships - simplified
    tags = models.ManyToManyField(Tag, blank=True)

    # Media
    image = models.ImageField(
        null=True, blank=True, upload_to=recipe_image_file_path
    )

    # Public/Private flag
    is_public = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]
        # Ensure user can't have duplicate recipe titles
        unique_together = ["user", "title"]


class RecipeIngredient(models.Model):
    """Simple junction table for recipe ingredients with quantities."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.CharField(
        max_length=100, help_text="e.g., '2 cups', '1 tbsp', '500g'"
    )

    # Optional notes for this specific ingredient in this recipe
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("recipe", "ingredient")
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} {self.ingredient.name}"
