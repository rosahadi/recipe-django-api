from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Recipe, Tag, Ingredient

User = get_user_model()


class RecipeApiTests(TestCase):
    """Test the recipe API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        self.client.force_authenticate(self.user)

        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Sample recipe',
            time_minutes=30,
            difficulty='easy',
            servings=4,
            instructions='Sample instructions',
            is_public=True
        )

        self.tag = Tag.objects.create(name='Test Tag', slug='test-tag')
        self.ingredient = Ingredient.objects.create(name='Test Ingredient')

        self.recipe.tags.add(self.tag)
        self.recipe.recipe_ingredients.create(
            ingredient=self.ingredient,
            quantity='100g'
        )

    def test_get_recipes_list(self):
        """Test retrieving a list of recipes."""
        res = self.client.get('/api/recipes/')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['title'], self.recipe.title)

    def test_create_recipe(self):
        """Test creating a new recipe."""
        payload = {
            'title': 'New recipe',
            'time_minutes': 45,
            'difficulty': 'medium',
            'servings': 2,
            'instructions': 'New instructions',
            'is_public': True,
            'tag_names': ['tag1', 'tag2'],
            'recipe_ingredients': [
                {
                    'ingredient_name': 'ingredient1',
                    'quantity': '200g'
                }
            ]
        }

        res = self.client.post('/api/recipes/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertIn('data', res.data)
        self.assertIn('title', res.data['data'])
        self.assertEqual(res.data['data']['title'], payload['title'])

        recipe = Recipe.objects.filter(title=payload['title']).first()
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe.tags.count(), 2)
        self.assertEqual(recipe.recipe_ingredients.count(), 1)

    def test_update_recipe(self):
        """Test updating a recipe."""
        payload = {
            'title': 'Updated recipe',
            'time_minutes': 60,
            'difficulty': 'hard',
            'servings': 6,
            'instructions': 'Updated instructions',
            'is_public': False
        }

        url = f'/api/recipes/{self.recipe.id}/'
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.title, payload['title'])
        self.assertEqual(self.recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(self.recipe.is_public, payload['is_public'])

    def test_delete_recipe(self):
        """Test deleting a recipe."""
        url = f'/api/recipes/{self.recipe.id}/'
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(Recipe.objects.filter(id=self.recipe.id).exists())
