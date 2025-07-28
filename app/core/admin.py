from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core import models


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users."""

    ordering = ["id"]
    list_display = ["email", "name", "is_active", "is_staff", "created_at"]
    list_filter = ["is_active", "is_staff", "is_superuser", "created_at"]
    search_fields = ["email", "name"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
        (
            "Email Verification",
            {
                "fields": (
                    "email_verification_token",
                    "email_verification_sent_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["last_login", "created_at"]

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "name",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


class RecipeIngredientInline(admin.TabularInline):
    """Inline admin for recipe ingredients."""

    model = models.RecipeIngredient
    extra = 1
    autocomplete_fields = ["ingredient"]


@admin.register(models.Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Admin for recipes."""

    list_display = [
        "title",
        "user",
        "difficulty",
        "time_minutes",
        "servings",
        "created_at",
    ]
    list_filter = ["difficulty", "created_at", "tags"]
    search_fields = ["title", "description", "user__email"]
    autocomplete_fields = ["user"]
    filter_horizontal = ["tags"]
    inlines = [RecipeIngredientInline]

    fieldsets = (
        ("Basic Information", {"fields": ("title", "description", "user")}),
        (
            "Recipe Details",
            {
                "fields": (
                    "instructions",
                    "time_minutes",
                    "difficulty",
                    "servings",
                )
            },
        ),
        ("Media", {"fields": ("image",)}),
        ("Tags", {"fields": ("tags",)}),
    )

    readonly_fields = ["created_at", "updated_at"]


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin for tags."""

    list_display = ["name", "recipe_count", "created_at"]
    search_fields = ["name"]
    ordering = ["name"]

    def recipe_count(self, obj):
        """Display count of recipes using this tag."""
        return obj.recipe_set.count()

    recipe_count.short_description = "Recipes"


@admin.register(models.Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Admin for ingredients."""

    list_display = ["name", "recipe_count", "created_at"]
    search_fields = ["name"]
    ordering = ["name"]

    def recipe_count(self, obj):
        """Display count of recipes using this ingredient."""
        return obj.recipeingredient_set.count()

    recipe_count.short_description = "Recipes"
