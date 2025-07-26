import uuid
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from core.models import Tag, Ingredient, Recipe, RecipeIngredient


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


class TagModelTests(TestCase):
    def test_create_tag_successful(self):
        tag = Tag.objects.create(name="Vegetarian")
        self.assertEqual(tag.name, "Vegetarian")
        self.assertEqual(str(tag), "Vegetarian")

    def test_tag_name_unique(self):
        Tag.objects.create(name="Vegan")
        with self.assertRaises(Exception):
            Tag.objects.create(name="Vegan")

    def test_tag_max_length(self):
        long_name = "a" * 256
        with self.assertRaises(ValidationError):
            tag = Tag(name=long_name)
            tag.full_clean()


class IngredientModelTests(TestCase):
    def test_create_ingredient_successful(self):
        ingredient = Ingredient.objects.create(name="Tomato")
        self.assertEqual(ingredient.name, "Tomato")
        self.assertEqual(str(ingredient), "Tomato")

    def test_ingredient_name_unique(self):
        Ingredient.objects.create(name="Onion")
        with self.assertRaises(Exception):
            Ingredient.objects.create(name="Onion")

    def test_ingredient_max_length(self):
        long_name = "a" * 256
        with self.assertRaises(ValidationError):
            ingredient = Ingredient(name=long_name)
            ingredient.full_clean()


class RecipeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="chef@example.com", name="Chef User", password="chefpass123"
        )
        self.tag1 = Tag.objects.create(name="Vegetarian")
        self.tag2 = Tag.objects.create(name="Quick")
        self.ingredient1 = Ingredient.objects.create(name="Tomato")
        self.ingredient2 = Ingredient.objects.create(name="Basil")

    def test_create_recipe_successful(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Tomato Basil Pasta",
            description="A simple and delicious pasta dish",
            instructions="Cook pasta, add tomatoes and basil",
            time_minutes=30,
            difficulty="easy",
            servings=4
        )

        self.assertEqual(recipe.user, self.user)
        self.assertEqual(recipe.title, "Tomato Basil Pasta")
        self.assertEqual(recipe.description, "A simple and delicious pasta dish")
        self.assertEqual(recipe.instructions, "Cook pasta, add tomatoes and basil")
        self.assertEqual(recipe.time_minutes, 30)
        self.assertEqual(recipe.difficulty, "easy")
        self.assertEqual(recipe.servings, 4)
        self.assertEqual(str(recipe), "Tomato Basil Pasta")

    def test_recipe_default_values(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            instructions="Test instructions",
            time_minutes=15
        )

        self.assertEqual(recipe.difficulty, "easy")
        self.assertEqual(recipe.servings, 4)
        self.assertEqual(recipe.description, "")

    def test_recipe_difficulty_choices(self):
        # Test valid choices
        for difficulty in ['easy', 'medium', 'hard']:
            recipe = Recipe.objects.create(
                user=self.user,
                title=f"Recipe {difficulty}",
                instructions="Test instructions",
                time_minutes=15,
                difficulty=difficulty
            )
            self.assertEqual(recipe.difficulty, difficulty)

    def test_recipe_time_minutes_validation(self):
        # Test minimum value validation
        with self.assertRaises(ValidationError):
            recipe = Recipe(
                user=self.user,
                title="Invalid Recipe",
                instructions="Test instructions",
                time_minutes=0  # Should be at least 1
            )
            recipe.full_clean()

    def test_recipe_servings_validation(self):
        # Test minimum value validation
        with self.assertRaises(ValidationError):
            recipe = Recipe(
                user=self.user,
                title="Invalid Recipe",
                instructions="Test instructions",
                time_minutes=15,
                servings=0  # Should be at least 1
            )
            recipe.full_clean()

    def test_recipe_with_tags(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Tagged Recipe",
            instructions="Test instructions",
            time_minutes=20
        )

        recipe.tags.add(self.tag1, self.tag2)

        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(self.tag1, recipe.tags.all())
        self.assertIn(self.tag2, recipe.tags.all())

    def test_recipe_cascade_delete_with_user(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            instructions="Test instructions",
            time_minutes=15
        )

        recipe_id = recipe.id
        self.user.delete()

        with self.assertRaises(Recipe.DoesNotExist):
            Recipe.objects.get(id=recipe_id)

    def test_recipe_image_upload_path(self):
        # Test the image upload path function
        from core.models import recipe_image_file_path

        recipe = Recipe.objects.create(
            user=self.user,
            title="Recipe with Image",
            instructions="Test instructions",
            time_minutes=15
        )

        path = recipe_image_file_path(recipe, "test_image.jpg")

        self.assertTrue(path.startswith("uploads/recipe/"))
        self.assertTrue(path.endswith(".jpg"))
        # Should contain a UUID (36 characters + extension)
        filename = path.split("/")[-1]
        self.assertEqual(len(filename), 40)  # 36 chars UUID + '.jpg' (4 chars)


class RecipeIngredientModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="chef@example.com", name="Chef User", password="chefpass123"
        )
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            instructions="Test instructions",
            time_minutes=30
        )
        self.ingredient = Ingredient.objects.create(name="Flour")

    def test_create_recipe_ingredient_successful(self):
        recipe_ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity="2 cups"
        )

        self.assertEqual(recipe_ingredient.recipe, self.recipe)
        self.assertEqual(recipe_ingredient.ingredient, self.ingredient)
        self.assertEqual(recipe_ingredient.quantity, "2 cups")
        self.assertEqual(str(recipe_ingredient), "2 cups Flour")

    def test_recipe_ingredient_quantity_variations(self):
        # Test different quantity formats
        quantities = ["1 tbsp", "500g", "2 large", "1/2 cup", "a pinch"]

        for i, quantity in enumerate(quantities):
            ingredient = Ingredient.objects.create(name=f"Ingredient{i}")
            recipe_ingredient = RecipeIngredient.objects.create(
                recipe=self.recipe,
                ingredient=ingredient,
                quantity=quantity
            )
            self.assertEqual(recipe_ingredient.quantity, quantity)

    def test_recipe_ingredient_cascade_delete_recipe(self):
        recipe_ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity="1 cup"
        )

        recipe_ingredient_id = recipe_ingredient.id
        self.recipe.delete()

        with self.assertRaises(RecipeIngredient.DoesNotExist):
            RecipeIngredient.objects.get(id=recipe_ingredient_id)

    def test_recipe_ingredient_cascade_delete_ingredient(self):
        recipe_ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity="1 cup"
        )

        recipe_ingredient_id = recipe_ingredient.id
        self.ingredient.delete()

        with self.assertRaises(RecipeIngredient.DoesNotExist):
            RecipeIngredient.objects.get(id=recipe_ingredient_id)

    def test_recipe_multiple_ingredients(self):
        # Test a recipe with multiple ingredients
        ingredients_data = [
            (Ingredient.objects.create(name="Salt"), "1 tsp"),
            (Ingredient.objects.create(name="Pepper"), "1/2 tsp"),
            (Ingredient.objects.create(name="Oil"), "2 tbsp"),
        ]

        for ingredient, quantity in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=self.recipe,
                ingredient=ingredient,
                quantity=quantity
            )

        recipe_ingredients = RecipeIngredient.objects.filter(recipe=self.recipe)
        self.assertEqual(recipe_ingredients.count(), 3)

        quantities = [ri.quantity for ri in recipe_ingredients]
        self.assertIn("1 tsp", quantities)
        self.assertIn("1/2 tsp", quantities)
        self.assertIn("2 tbsp", quantities)

    def test_ingredient_multiple_recipes(self):
        # Test an ingredient used in multiple recipes
        recipe2 = Recipe.objects.create(
            user=self.user,
            title="Another Recipe",
            instructions="Different instructions",
            time_minutes=45
        )

        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity="1 cup"
        )

        RecipeIngredient.objects.create(
            recipe=recipe2,
            ingredient=self.ingredient,
            quantity="2 cups"
        )

        recipe_ingredients = RecipeIngredient.objects.filter(ingredient=self.ingredient)
        self.assertEqual(recipe_ingredients.count(), 2)

        recipes = [ri.recipe for ri in recipe_ingredients]
        self.assertIn(self.recipe, recipes)
        self.assertIn(recipe2, recipes)


class RecipeIntegrationTests(TestCase):
    """Integration tests for Recipe model relationships"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="chef@example.com", name="Chef User", password="chefpass123"
        )

    def test_complete_recipe_creation(self):
        # Create a complete recipe with tags and ingredients
        recipe = Recipe.objects.create(
            user=self.user,
            title="Spaghetti Carbonara",
            description="Classic Italian pasta dish",
            instructions="Cook pasta, mix with eggs and cheese",
            time_minutes=25,
            difficulty="medium",
            servings=4
        )

        # Add tags
        italian_tag = Tag.objects.create(name="Italian")
        quick_tag = Tag.objects.create(name="Quick")
        recipe.tags.add(italian_tag, quick_tag)

        # Add ingredients
        pasta = Ingredient.objects.create(name="Spaghetti")
        eggs = Ingredient.objects.create(name="Eggs")
        cheese = Ingredient.objects.create(name="Parmesan")

        RecipeIngredient.objects.create(recipe=recipe,
                                        ingredient=pasta,
                                        quantity="400g")
        RecipeIngredient.objects.create(recipe=recipe,
                                        ingredient=eggs,
                                        quantity="4 large")
        RecipeIngredient.objects.create(recipe=recipe,
                                        ingredient=cheese,
                                        quantity="100g grated")

        self.assertEqual(recipe.tags.count(), 2)
        self.assertEqual(recipe.ingredients.count(), 3)

        recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)
        self.assertEqual(recipe_ingredients.count(), 3)

        pasta_in_recipe = RecipeIngredient.objects.get(recipe=recipe, ingredient=pasta)
        self.assertEqual(pasta_in_recipe.quantity, "400g")
