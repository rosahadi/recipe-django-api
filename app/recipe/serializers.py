from rest_framework import serializers
from core.models import Recipe, Tag, Ingredient, RecipeIngredient
from django.db import transaction
import re


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tag objects"""

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']

    def validate_name(self, value):
        """Ensure tag name is unique (case-insensitive)"""
        if Tag.objects.filter(name__iexact=value).exists():
            if self.instance and self.instance.name.lower() == value.lower():
                return value
            raise serializers.ValidationError("Tag with this name already exists.")
        return value.strip().lower()


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for ingredient objects"""

    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only_fields = ['id']

    def validate_name(self, value):
        """Ensure ingredient name is unique (case-insensitive)"""
        if Ingredient.objects.filter(name__iexact=value).exists():
            if self.instance and self.instance.name.lower() == value.lower():
                return value
            raise serializers.ValidationError(
                "Ingredient with this name already exists."
                )
        return value.strip().lower()


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Serializer for recipe ingredient relationships"""

    ingredient_id = serializers.IntegerField(write_only=True)
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'ingredient_id', 'ingredient', 'quantity']
        read_only_fields = ['id']

    def validate_quantity(self, value):
        """Validate quantity format and content"""
        if not value or not value.strip():
            raise serializers.ValidationError("Quantity cannot be empty.")

        cleaned_quantity = value.strip()

        if len(cleaned_quantity) > 50:
            raise serializers.ValidationError(
                "Quantity is too long (max 50 characters)."
                )

        if not re.search(r'\d', cleaned_quantity):
            raise serializers.ValidationError(
                "Quantity must contain at least one number."
            )

        # Validate that the quantity only includes digits, letters,
        #  spaces, and common measurement symbols (e.g., 1/2 cup, 200g)
        if not re.match(r'^[0-9\s\-\.,/()a-zA-Z]+$', cleaned_quantity):
            raise serializers.ValidationError(
                "Quantity contains invalid characters."
            )

        return cleaned_quantity

    def validate_ingredient_id(self, value):
        """Ensure ingredient exists"""
        try:
            Ingredient.objects.get(id=value)
        except Ingredient.DoesNotExist:
            raise serializers.ValidationError(f"Invalid ingredient ID: {value}")
        return value


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipe objects"""

    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipeingredient_set',
        many=True,
        read_only=True
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    recipe_ingredients = RecipeIngredientSerializer(
        many=True,
        write_only=True,
        required=False,
        allow_empty=True
    )
    user = serializers.StringRelatedField(read_only=True)
    image = serializers.ImageField(required=False)

    class Meta:
        model = Recipe
        fields = [
            'id', 'title', 'description', 'instructions', 'time_minutes',
            'difficulty', 'servings', 'tags', 'ingredients', 'image',
            'tag_ids', 'recipe_ingredients', 'user'
        ]
        read_only_fields = ['id', 'user']

    def validate_title(self, value):
        """Validate recipe title"""
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")

        cleaned_title = value.strip()

        if len(cleaned_title) < 3:
            raise serializers.ValidationError(
                "Title must be at least 3 characters long."
                )

        if len(cleaned_title) > 255:
            raise serializers.ValidationError("Title is too long (max 255 characters).")

        return cleaned_title

    def validate_instructions(self, value):
        """Validate recipe instructions"""
        if not value or not value.strip():
            raise serializers.ValidationError("Instructions cannot be empty.")

        cleaned_instructions = value.strip()

        if len(cleaned_instructions) < 10:
            raise serializers.ValidationError(
                "Instructions must be at least 10 characters long."
            )

        return cleaned_instructions

    def validate_time_minutes(self, value):
        """Validate cooking time"""
        if value is None:
            raise serializers.ValidationError("Time minutes is required.")

        if value < 1:
            raise serializers.ValidationError("Time must be at least 1 minute.")

        if value > 1440:
            raise serializers.ValidationError(
                "Time cannot exceed 24 hours (1440 minutes)."
                )

        return value

    def validate_servings(self, value):
        """Validate number of servings"""
        if value is None:
            raise serializers.ValidationError("Servings is required.")

        if value < 1:
            raise serializers.ValidationError("Servings must be at least 1.")

        if value > 50:
            raise serializers.ValidationError("Servings cannot exceed 50.")

        return value

    def validate_tag_ids(self, value):
        """Validate tag IDs exist"""
        if not value:
            return value

        # Remove duplicates while preserving order
        unique_ids = list(dict.fromkeys(value))

        # Check if all tag IDs exist
        existing_tags = Tag.objects.filter(id__in=unique_ids)
        if len(existing_tags) != len(unique_ids):
            existing_ids = set(existing_tags.values_list('id', flat=True))
            invalid_ids = set(unique_ids) - existing_ids
            raise serializers.ValidationError(
                f"Invalid tag IDs: {list(invalid_ids)}"
            )

        return unique_ids

    def validate_recipe_ingredients(self, value):
        """Validate recipe ingredients"""
        if not value:
            return value

        ingredient_ids = [item['ingredient_id'] for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Duplicate ingredients are not allowed."
            )

        return value

    def validate(self, attrs):
        """Cross-field validation"""
        # Ensure recipe has at least one ingredient
        recipe_ingredients = attrs.get('recipe_ingredients', [])
        if not recipe_ingredients and not self.instance:
            raise serializers.ValidationError(
                "Recipe must have at least one ingredient."
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create recipe with tags and ingredients"""
        tag_ids = validated_data.pop('tag_ids', [])
        recipe_ingredients_data = validated_data.pop('recipe_ingredients', [])

        # Create recipe
        recipe = Recipe.objects.create(**validated_data)

        # Add tags
        if tag_ids:
            recipe.tags.set(tag_ids)

        # Add ingredients
        for ingredient_data in recipe_ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data['ingredient_id'],
                quantity=ingredient_data['quantity']
            )

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update recipe with tags and ingredients"""
        tag_ids = validated_data.pop('tag_ids', None)
        recipe_ingredients_data = validated_data.pop('recipe_ingredients', None)

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags if provided
        if tag_ids is not None:
            instance.tags.set(tag_ids)

        # Update ingredients if provided
        if recipe_ingredients_data is not None:
            # Remove existing ingredients
            instance.recipeingredient_set.all().delete()

            # Add new ingredients
            for ingredient_data in recipe_ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient_id=ingredient_data['ingredient_id'],
                    quantity=ingredient_data['quantity']
                )

        return instance


class RecipeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for recipe lists"""

    tags = TagSerializer(many=True, read_only=True)
    ingredient_count = serializers.SerializerMethodField()
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Recipe
        fields = [
            'id', 'title', 'description', 'time_minutes', 'difficulty',
            'servings', 'tags', 'ingredient_count', 'image', 'user'
        ]
        read_only_fields = ['id', 'user']

    def get_ingredient_count(self, obj):
        """Get count of ingredients for this recipe"""
        return obj.recipeingredient_set.count()


class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading recipe images"""

    class Meta:
        model = Recipe
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {
            'image': {'required': True}
        }
