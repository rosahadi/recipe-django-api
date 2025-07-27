import uuid
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
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
        self.assertIsNotNone(self.user.created_at)

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
        """Tags should be created with proper defaults"""
        tag = Tag.objects.create(name="Vegetarian", slug="vegetarian")
        self.assertEqual(tag.name, "Vegetarian")
        self.assertEqual(tag.slug, "vegetarian")
        self.assertEqual(tag.usage_count, 0)
        self.assertEqual(str(tag), "Vegetarian")
        self.assertIsNotNone(tag.created_at)
        self.assertIsNotNone(tag.updated_at)

    def test_tag_name_unique(self):
        """Tag names should be unique across the system"""
        Tag.objects.create(name="Vegan", slug="vegan")
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="Vegan", slug="vegan-2")

    def test_tag_slug_unique(self):
        """Tag slugs should be unique for URL purposes"""
        Tag.objects.create(name="Italian", slug="italian")
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="Italian Cuisine", slug="italian")

    def test_tag_max_length(self):
        """Tag names shouldn't be too long for database efficiency"""
        long_name = "a" * 256
        with self.assertRaises(ValidationError):
            tag = Tag(name=long_name, slug="test-slug")
            tag.full_clean()

    def test_tag_ordering(self):
        """Tags should be ordered alphabetically for better UX"""
        Tag.objects.create(name="Zucchini", slug="zucchini")
        Tag.objects.create(name="Apple", slug="apple")
        Tag.objects.create(name="Banana", slug="banana")

        tags = list(Tag.objects.all())
        tag_names = [tag.name for tag in tags]
        self.assertEqual(tag_names, ["Apple", "Banana", "Zucchini"])

    def test_increment_usage(self):
        """Usage count should increase when tags are used in recipes"""
        tag = Tag.objects.create(name="Spicy", slug="spicy")
        self.assertEqual(tag.usage_count, 0)

        tag.increment_usage()
        tag.refresh_from_db()
        self.assertEqual(tag.usage_count, 1)

    def test_decrement_usage(self):
        """Usage count should decrease when tags are removed from recipes"""
        tag = Tag.objects.create(name="Sweet", slug="sweet")
        tag.usage_count = 3
        tag.save()

        tag.decrement_usage()
        tag.refresh_from_db()
        self.assertEqual(tag.usage_count, 2)

    def test_decrement_usage_cannot_go_negative(self):
        """Usage count should never go below zero"""
        tag = Tag.objects.create(name="Healthy", slug="healthy")
        self.assertEqual(tag.usage_count, 0)

        tag.decrement_usage()
        tag.refresh_from_db()
        self.assertEqual(tag.usage_count, 0)

    def test_tag_timestamps_update(self):
        """Updated timestamp should change when tags are modified"""
        tag = Tag.objects.create(name="Original", slug="original")
        original_updated = tag.updated_at

        import time
        time.sleep(0.01)

        tag.name = "Updated"
        tag.save()

        self.assertGreater(tag.updated_at, original_updated)


class IngredientModelTests(TestCase):
    def test_create_ingredient_successful(self):
        """Ingredients should be created with proper defaults"""
        ingredient = Ingredient.objects.create(name="Tomato", category="Vegetable")
        self.assertEqual(ingredient.name, "Tomato")
        self.assertEqual(ingredient.category, "Vegetable")
        self.assertEqual(ingredient.usage_count, 0)
        self.assertEqual(str(ingredient), "Tomato")
        # Check timestamp fields
        self.assertIsNotNone(ingredient.created_at)
        self.assertIsNotNone(ingredient.updated_at)

    def test_create_ingredient_without_category(self):
        """Ingredients should work fine without a category"""
        ingredient = Ingredient.objects.create(name="Salt")
        self.assertEqual(ingredient.category, "")

    def test_ingredient_name_unique(self):
        """Ingredient names should be unique to avoid duplicates"""
        Ingredient.objects.create(name="Onion")
        with self.assertRaises(IntegrityError):
            Ingredient.objects.create(name="Onion")

    def test_ingredient_max_length(self):
        """Ingredient names shouldn't be too long"""
        long_name = "a" * 256
        with self.assertRaises(ValidationError):
            ingredient = Ingredient(name=long_name)
            ingredient.full_clean()

    def test_ingredient_ordering(self):
        """Ingredients should be sorted alphabetically for easy browsing"""
        Ingredient.objects.create(name="Zucchini")
        Ingredient.objects.create(name="Apple")
        Ingredient.objects.create(name="Banana")

        ingredients = list(Ingredient.objects.all())
        ingredient_names = [ingredient.name for ingredient in ingredients]
        self.assertEqual(ingredient_names, ["Apple", "Banana", "Zucchini"])

    def test_increment_usage(self):
        """Usage count should track how often ingredients are used"""
        ingredient = Ingredient.objects.create(name="Garlic")
        self.assertEqual(ingredient.usage_count, 0)

        ingredient.increment_usage()
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.usage_count, 1)

    def test_decrement_usage(self):
        """Usage count should decrease when ingredients are removed"""
        ingredient = Ingredient.objects.create(name="Pepper")
        ingredient.usage_count = 5
        ingredient.save()

        ingredient.decrement_usage()
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.usage_count, 4)

    def test_decrement_usage_stops_at_zero(self):
        """Usage count should never become negative"""
        ingredient = Ingredient.objects.create(name="Oregano")
        self.assertEqual(ingredient.usage_count, 0)

        ingredient.decrement_usage()
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.usage_count, 0)

    def test_ingredient_timestamps_update(self):
        """Timestamps should update when ingredients are modified"""
        ingredient = Ingredient.objects.create(name="Original")
        original_updated = ingredient.updated_at

        import time
        time.sleep(0.01)

        ingredient.name = "Updated"
        ingredient.save()

        self.assertGreater(ingredient.updated_at, original_updated)


class RecipeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="chef@example.com", name="Chef User", password="chefpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", name="Other User", password="pass123"
        )
        self.tag1 = Tag.objects.create(name="Vegetarian", slug="vegetarian")
        self.tag2 = Tag.objects.create(name="Quick", slug="quick")
        self.ingredient1 = Ingredient.objects.create(name="Tomato")
        self.ingredient2 = Ingredient.objects.create(name="Basil")

    def test_create_recipe_successful(self):
        """Recipes should be created with all required fields"""
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
        self.assertTrue(recipe.is_public)
        self.assertEqual(str(recipe), "Tomato Basil Pasta")
        self.assertIsNotNone(recipe.created_at)
        self.assertIsNotNone(recipe.updated_at)

    def test_recipe_default_values(self):
        """Recipes should have sensible defaults"""
        recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            instructions="Test instructions",
            time_minutes=15
        )

        self.assertEqual(recipe.difficulty, "easy")
        self.assertEqual(recipe.servings, 4)
        self.assertEqual(recipe.description, "")
        self.assertTrue(recipe.is_public)

    def test_recipe_can_be_private(self):
        """Users should be able to create private recipes"""
        recipe = Recipe.objects.create(
            user=self.user,
            title="Secret Recipe",
            instructions="Top secret",
            time_minutes=60,
            is_public=False
        )
        self.assertFalse(recipe.is_public)

    def test_recipe_difficulty_choices(self):
        """All difficulty levels should work correctly"""
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
        """Recipes need at least 1 minute cooking time"""
        with self.assertRaises(ValidationError):
            recipe = Recipe(
                user=self.user,
                title="Invalid Recipe",
                instructions="Test instructions",
                time_minutes=0
            )
            recipe.full_clean()

    def test_recipe_servings_validation(self):
        """Recipes should serve at least 1 person"""
        with self.assertRaises(ValidationError):
            recipe = Recipe(
                user=self.user,
                title="Invalid Recipe",
                instructions="Test instructions",
                time_minutes=15,
                servings=0
            )
            recipe.full_clean()

    def test_recipe_unique_title_per_user(self):
        """Users can't have duplicate recipe titles"""
        Recipe.objects.create(
            user=self.user,
            title="Pasta Recipe",
            instructions="Make pasta",
            time_minutes=20
        )

        with self.assertRaises(IntegrityError):
            Recipe.objects.create(
                user=self.user,
                title="Pasta Recipe",
                instructions="Different pasta",
                time_minutes=30
            )

    def test_different_users_can_have_same_recipe_title(self):
        """Different users should be able to use the same recipe title"""
        Recipe.objects.create(
            user=self.user,
            title="Pasta Recipe",
            instructions="User 1's pasta",
            time_minutes=20
        )

        recipe2 = Recipe.objects.create(
            user=self.other_user,
            title="Pasta Recipe",
            instructions="User 2's pasta",
            time_minutes=25
        )

        self.assertEqual(recipe2.title, "Pasta Recipe")
        self.assertEqual(recipe2.user, self.other_user)

    def test_recipe_with_tags(self):
        """Recipes should support multiple tags"""
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
        """Recipes should be deleted when their owner is deleted"""
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
        """Recipe images should be stored in the right location with unique names"""
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
        filename = path.split("/")[-1]
        self.assertEqual(len(filename), 40)  # 36 char UUID + '.jpg'

    def test_recipe_ordering(self):
        """Recipes should be ordered by creation date, newest first"""
        recipe1 = Recipe.objects.create(
            user=self.user,
            title="First Recipe",
            instructions="First",
            time_minutes=10
        )

        import time
        time.sleep(0.01)  # Ensure different timestamps

        recipe2 = Recipe.objects.create(
            user=self.user,
            title="Second Recipe",
            instructions="Second",
            time_minutes=15
        )

        recipes = list(Recipe.objects.all())
        self.assertEqual(recipes[0], recipe2)
        self.assertEqual(recipes[1], recipe1)

    def test_recipe_timestamps_update(self):
        """Recipe timestamps should update when modified"""
        recipe = Recipe.objects.create(
            user=self.user,
            title="Original Title",
            instructions="Test instructions",
            time_minutes=15
        )
        original_updated = recipe.updated_at

        import time
        time.sleep(0.01)

        recipe.title = "Updated Title"
        recipe.save()

        self.assertGreater(recipe.updated_at, original_updated)


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
        """Recipe ingredients should link recipes and ingredients with quantities"""
        recipe_ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity="2 cups"
        )

        self.assertEqual(recipe_ingredient.recipe, self.recipe)
        self.assertEqual(recipe_ingredient.ingredient, self.ingredient)
        self.assertEqual(recipe_ingredient.quantity, "2 cups")
        self.assertEqual(recipe_ingredient.notes, "")
        self.assertEqual(str(recipe_ingredient), "2 cups Flour")

    def test_recipe_ingredient_with_notes(self):
        """Recipe ingredients should support optional notes"""
        recipe_ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity="1 cup",
            notes="sifted, room temperature"
        )

        self.assertEqual(recipe_ingredient.notes, "sifted, room temperature")

    def test_recipe_ingredient_unique_together(self):
        """Each ingredient should only appear once per recipe"""
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity="1 cup"
        )

        with self.assertRaises(IntegrityError):
            RecipeIngredient.objects.create(
                recipe=self.recipe,
                ingredient=self.ingredient,
                quantity="2 cups"
            )

    def test_recipe_ingredient_quantity_variations(self):
        """Recipe ingredients should handle various quantity formats"""
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
        """Recipe ingredients should be deleted when their recipe is deleted"""
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
        """Recipe ingredients should be deleted when their ingredient is deleted"""
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
        """Recipes should support multiple ingredients with different quantities"""
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
        """Ingredients should be reusable across different recipes"""
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
    """Tests that check how all the models work together"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="chef@example.com", name="Chef User", password="chefpass123"
        )

    def test_complete_recipe_creation(self):
        """Test creating a full recipe with tags and ingredients"""
        recipe = Recipe.objects.create(
            user=self.user,
            title="Spaghetti Carbonara",
            description="Classic Italian pasta dish",
            instructions="Cook pasta, mix with eggs and cheese",
            time_minutes=25,
            difficulty="medium",
            servings=4
        )

        # Add some tags
        italian_tag = Tag.objects.create(name="Italian", slug="italian")
        quick_tag = Tag.objects.create(name="Quick", slug="quick")
        recipe.tags.add(italian_tag, quick_tag)

        # Add ingredients with quantities
        pasta = Ingredient.objects.create(name="Spaghetti", category="Pasta")
        eggs = Ingredient.objects.create(name="Eggs", category="Dairy")
        cheese = Ingredient.objects.create(name="Parmesan", category="Cheese")

        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=pasta,
            quantity="400g"
        )
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=eggs,
            quantity="4 large",
            notes="room temperature works best"
        )
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=cheese,
            quantity="100g grated"
        )

        # Verify everything is connected properly
        self.assertEqual(recipe.tags.count(), 2)
        self.assertEqual(recipe.recipe_ingredients.count(), 3)

        recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)
        self.assertEqual(recipe_ingredients.count(), 3)

        pasta_in_recipe = RecipeIngredient.objects.get(recipe=recipe, ingredient=pasta)
        self.assertEqual(pasta_in_recipe.quantity, "400g")

        eggs_in_recipe = RecipeIngredient.objects.get(recipe=recipe, ingredient=eggs)
        self.assertEqual(eggs_in_recipe.notes, "room temperature works best")

    def test_recipe_with_same_ingredient_different_quantities(self):
        """Same ingredient should work in different recipes with different amounts"""
        recipe1 = Recipe.objects.create(
            user=self.user,
            title="Small Cake",
            instructions="Make a small cake",
            time_minutes=30
        )

        recipe2 = Recipe.objects.create(
            user=self.user,
            title="Large Cake",
            instructions="Make a large cake",
            time_minutes=60
        )

        flour = Ingredient.objects.create(name="Flour", category="Baking")

        RecipeIngredient.objects.create(
            recipe=recipe1,
            ingredient=flour,
            quantity="1 cup"
        )

        RecipeIngredient.objects.create(
            recipe=recipe2,
            ingredient=flour,
            quantity="3 cups"
        )

        flour_in_recipe1 = RecipeIngredient.objects.get(
            recipe=recipe1,
            ingredient=flour
        )
        flour_in_recipe2 = RecipeIngredient.objects.get(
            recipe=recipe2,
            ingredient=flour
        )

        self.assertEqual(flour_in_recipe1.quantity, "1 cup")
        self.assertEqual(flour_in_recipe2.quantity, "3 cups")

    def test_public_vs_private_recipes(self):
        """Test the privacy settings work correctly"""
        public_recipe = Recipe.objects.create(
            user=self.user,
            title="Public Recipe",
            instructions="Everyone can see this",
            time_minutes=20,
            is_public=True
        )

        private_recipe = Recipe.objects.create(
            user=self.user,
            title="Secret Recipe",
            instructions="Only I can see this",
            time_minutes=30,
            is_public=False
        )

        # Test filtering
        public_recipes = Recipe.objects.filter(is_public=True)
        private_recipes = Recipe.objects.filter(is_public=False)

        self.assertIn(public_recipe, public_recipes)
        self.assertNotIn(private_recipe, public_recipes)
        self.assertIn(private_recipe, private_recipes)
        self.assertNotIn(public_recipe, private_recipes)


class TimeStampedModelTests(TestCase):
    """Test the base timestamp functionality that all models inherit"""

    def test_created_at_set_on_creation(self):
        """All models should get a creation timestamp"""
        tag = Tag.objects.create(name="Test Tag", slug="test-tag")
        self.assertIsNotNone(tag.created_at)
        self.assertLessEqual(
            tag.created_at,
            timezone.now()
        )

    def test_updated_at_changes_on_modification(self):
        """The updated timestamp should change when models are modified"""
        tag = Tag.objects.create(name="Original Name", slug="original")
        original_created = tag.created_at
        original_updated = tag.updated_at

        import time
        time.sleep(0.01)

        tag.name = "Modified Name"
        tag.save()

        self.assertEqual(tag.created_at, original_created)
        self.assertGreater(tag.updated_at, original_updated)

    def test_timestamps_on_different_models(self):
        """All models should have working timestamps"""
        user = User.objects.create_user(
            email="test@example.com",
            name="Test User",
            password="pass123"
        )

        tag = Tag.objects.create(name="Test", slug="test")
        ingredient = Ingredient.objects.create(name="Test Ingredient")
        recipe = Recipe.objects.create(
            user=user,
            title="Test Recipe",
            instructions="Test",
            time_minutes=10
        )

        for model in [tag, ingredient, recipe]:
            self.assertIsNotNone(model.created_at)
            self.assertIsNotNone(model.updated_at)
