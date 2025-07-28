from rest_framework import serializers
from django.db import transaction
from django.utils.text import slugify
import re
import json

from core.models import Recipe, Tag, Ingredient, RecipeIngredient


class TagSerializer(serializers.ModelSerializer):
    """Serializer for recipe tags."""

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "usage_count", "created_at"]
        read_only_fields = ["id", "slug", "usage_count", "created_at"]

    def validate_name(self, value):
        """Validate and normalize tag name."""
        normalized_name = value.strip().lower()

        if len(normalized_name) < 2:
            raise serializers.ValidationError(
                "Tag name must be at least 2 characters long."
            )
        if len(normalized_name) > 50:
            raise serializers.ValidationError(
                "Tag name cannot exceed 50 characters."
            )

        # Check for duplicates
        qs = Tag.objects.filter(name__iexact=normalized_name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "A tag with this name already exists."
            )

        return normalized_name

    def create(self, validated_data):
        """Create tag with auto-generated slug."""
        validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for recipe ingredients."""

    class Meta:
        model = Ingredient
        fields = ["id", "name", "category", "usage_count", "created_at"]
        read_only_fields = ["id", "usage_count", "created_at"]

    def validate_name(self, value):
        """Validate and normalize ingredient name."""
        normalized_name = value.strip().lower()

        if len(normalized_name) < 2:
            raise serializers.ValidationError(
                "Ingredient name must be at least 2 characters long."
            )
        if len(normalized_name) > 100:
            raise serializers.ValidationError(
                "Ingredient name cannot exceed 100 characters."
            )

        # Check for duplicates
        qs = Ingredient.objects.filter(name__iexact=normalized_name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "An ingredient with this name already exists."
            )

        return normalized_name


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Serializer for recipe-specific ingredient details."""

    ingredient = IngredientSerializer(read_only=True)
    ingredient_name = serializers.CharField(write_only=True, max_length=255)

    class Meta:
        model = RecipeIngredient
        fields = ["id", "ingredient", "ingredient_name", "quantity", "notes"]
        read_only_fields = ["id"]

    def validate_quantity(self, value):
        """Ensure quantity is properly formatted."""
        if not value or not value.strip():
            raise serializers.ValidationError("Quantity is required.")

        cleaned = value.strip()
        if len(cleaned) > 100:
            raise serializers.ValidationError(
                "Quantity description is too long (max 100 characters)."
            )

        if not re.search(r"[\d\-\/\.]", cleaned):
            raise serializers.ValidationError(
                "Quantity should include numbers or fractions."
            )

        return cleaned


class RecipeSerializer(serializers.ModelSerializer):
    """Complete recipe serializer for create/update operations."""

    tags = TagSerializer(many=True, read_only=True)
    recipe_ingredients = RecipeIngredientSerializer(many=True, required=False)
    user = serializers.StringRelatedField(read_only=True)

    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text=(
            "List of tag names. "
            "Tags will be created automatically if they don't exist."
        ),
    )

    recipe_ingredients_json = serializers.CharField(
        write_only=True,
        required=False,
        help_text=(
            "JSON string of ingredients array - "
            "use this when uploading images via multipart form"
        ),
    )

    image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Recipe image file",
    )

    class Meta:
        model = Recipe
        fields = [
            "id",
            "title",
            "description",
            "instructions",
            "time_minutes",
            "difficulty",
            "servings",
            "is_public",
            "tags",
            "tag_names",
            "recipe_ingredients",
            "recipe_ingredients_json",
            "user",
            "image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def to_representation(self, instance):
        """Add full image URL to response."""
        data = super().to_representation(instance)

        if instance.image and hasattr(instance.image, "url"):
            request = self.context.get("request")
            if request:
                data["image"] = request.build_absolute_uri(instance.image.url)
            else:
                data["image"] = instance.image.url
        else:
            data["image"] = None

        return data

    def validate_title(self, value):
        """Ensure title is unique per user and properly formatted."""
        # Allow empty values for partial updates
        if not value and getattr(self, "partial", False):
            return value

        if not value or not value.strip():
            raise serializers.ValidationError("Title is required.")

        cleaned_title = value.strip()

        if len(cleaned_title) < 3:
            raise serializers.ValidationError(
                "Title must be at least 3 characters long."
            )
        if len(cleaned_title) > 200:
            raise serializers.ValidationError(
                "Title cannot exceed 200 characters."
            )

        # Check for duplicate titles within user's recipes
        user = (
            self.context.get("request").user
            if self.context.get("request")
            else None
        )
        if user and user.is_authenticated:
            qs = Recipe.objects.filter(user=user, title__iexact=cleaned_title)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "You already have a recipe with this title."
                )

        return cleaned_title

    def validate_recipe_ingredients_json(self, value):
        """Parse JSON string into ingredient data - needed for multipart uploads."""
        if not value:
            return []

        try:
            ingredients_data = json.loads(value)
        except json.JSONDecodeError:
            raise serializers.ValidationError(
                "Invalid JSON format for ingredients."
            )

        if not isinstance(ingredients_data, list):
            ingredients_data = [ingredients_data]

        validated_ingredients = []
        for ingredient_data in ingredients_data:
            serializer = RecipeIngredientSerializer(data=ingredient_data)
            if serializer.is_valid():
                validated_ingredients.append(serializer.validated_data)
            else:
                raise serializers.ValidationError(
                    f"Invalid ingredient: {serializer.errors}"
                )

        return validated_ingredients

    def validate(self, data):
        """Ensure recipe has ingredients using either field format."""
        recipe_ingredients = data.get("recipe_ingredients", [])
        recipe_ingredients_json = data.get("recipe_ingredients_json", [])

        if recipe_ingredients_json:
            data["recipe_ingredients"] = recipe_ingredients_json
        elif not recipe_ingredients and not self.partial:
            raise serializers.ValidationError(
                "Recipe must have at least one ingredient. "
                "Use 'recipe_ingredients' for JSON or "
                "'recipe_ingredients_json' for multipart uploads."
            )

        return data

    @transaction.atomic
    def create(self, validated_data):
        """Create recipe with related tags and ingredients."""
        tag_names = validated_data.pop("tag_names", [])
        recipe_ingredients_data = validated_data.pop("recipe_ingredients", [])
        validated_data.pop("recipe_ingredients_json", None)

        recipe = Recipe.objects.create(**validated_data)

        if tag_names:
            self._create_or_update_tags(recipe, tag_names)

        self._create_recipe_ingredients(recipe, recipe_ingredients_data)

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update recipe and related data."""
        tag_names = validated_data.pop("tag_names", None)
        recipe_ingredients_data = validated_data.pop("recipe_ingredients", None)
        validated_data.pop("recipe_ingredients_json", None)

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags if provided
        if tag_names is not None:
            self._update_tags(instance, tag_names)

        # Update ingredients if provided
        if recipe_ingredients_data is not None:
            self._update_ingredients(instance, recipe_ingredients_data)

        return instance

    def _create_or_update_tags(self, recipe, tag_names):
        """Create or get tags and associate with recipe."""
        tags = []
        for tag_name in tag_names:
            tag, created = Tag.objects.get_or_create(
                name__iexact=tag_name.lower(),
                defaults={"name": tag_name.lower(), "slug": slugify(tag_name)},
            )
            if not created:
                tag.increment_usage()
            else:
                tag.usage_count = 1
                tag.save()
            tags.append(tag)
        recipe.tags.set(tags)

    def _update_tags(self, recipe, tag_names):
        """Update recipe tags, handling usage counts."""
        for tag in recipe.tags.all():
            tag.decrement_usage()

        self._create_or_update_tags(recipe, tag_names)

    def _create_recipe_ingredients(self, recipe, ingredients_data):
        """Create recipe ingredients."""
        for ingredient_data in ingredients_data:
            ingredient_name = ingredient_data.pop("ingredient_name")

            ingredient, created = Ingredient.objects.get_or_create(
                name__iexact=ingredient_name.lower(),
                defaults={"name": ingredient_name.lower()},
            )

            if not created:
                ingredient.increment_usage()
            else:
                ingredient.usage_count = 1
                ingredient.save()

            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=ingredient, **ingredient_data
            )

    def _update_ingredients(self, recipe, ingredients_data):
        """Update recipe ingredients, handling usage counts."""
        for recipe_ingredient in recipe.recipe_ingredients.all():
            recipe_ingredient.ingredient.decrement_usage()

        recipe.recipe_ingredients.all().delete()
        self._create_recipe_ingredients(recipe, ingredients_data)


class RecipeListSerializer(serializers.ModelSerializer):
    """Serializer for recipe browsing."""

    tags = TagSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    ingredient_count = serializers.SerializerMethodField()
    description_preview = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id",
            "title",
            "description_preview",
            "time_minutes",
            "difficulty",
            "servings",
            "tags",
            "ingredient_count",
            "image",
            "user",
            "is_public",
            "created_at",
        ]

    def to_representation(self, instance):
        """Add full image URL to response."""
        data = super().to_representation(instance)

        if instance.image and hasattr(instance.image, "url"):
            request = self.context.get("request")
            if request:
                data["image"] = request.build_absolute_uri(instance.image.url)
            else:
                data["image"] = instance.image.url
        else:
            data["image"] = None

        return data

    def get_ingredient_count(self, obj):
        """Count ingredients in the recipe."""
        return obj.recipe_ingredients.count()

    def get_description_preview(self, obj):
        """Truncated description for list view."""
        if obj.description:
            return (
                obj.description[:150] + "..."
                if len(obj.description) > 150
                else obj.description
            )
        return ""
