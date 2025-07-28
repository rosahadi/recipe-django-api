from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes


# Tag ViewSet Schemas
tag_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Browse available tags",
        description=(
            "Get all tags that have been used in recipes. "
            "Tags are automatically created when recipes are posted."
        ),
    ),
    create=extend_schema(
        summary="Create a new tag",
        description=(
            "Create a tag manually (admin only)."
            " Tags are usually created automatically when recipes are posted."
        ),
    ),
)


# Ingredient ViewSet Schemas
ingredient_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Browse available ingredients",
        description=(
            "Get all ingredients that have been used in recipes. "
            "Ingredients are automatically created when recipes are posted."
        ),
    ),
)


# Recipe ViewSet Schemas
recipe_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="Browse recipes",
        description="""
        Browse all available recipes with advanced filtering options.

        Regular users see:
        - All public recipes
        - Their own recipes (public and private)

        Superusers see:
        - All recipes (public and private from all users)
        """,
        parameters=[
            OpenApiParameter(
                name="tags",
                description="Filter by tag names (comma-separated)",
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="ingredients",
                description="Filter by ingredient names (comma-separated)",
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="difficulty",
                description="Filter by difficulty level",
                type=OpenApiTypes.STR,
                enum=["easy", "medium", "hard"],
            ),
            OpenApiParameter(
                name="max_time",
                description="Maximum cooking time in minutes",
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="min_servings",
                description="Minimum number of servings",
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="my_recipes",
                description="Show only your own recipes (authentication required)",
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name="user_id",
                description="Show public recipes from a specific user",
                type=OpenApiTypes.INT,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create a new recipe",
        description="Create a new recipe with ingredients, tags, and optional image.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Recipe title (3-200 characters)",
                        "example": "Classic Spaghetti Carbonara",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional recipe description",
                        "example": (
                            "A traditional Italian pasta dish with eggs, cheese"
                        ),
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Step-by-step cooking instructions",
                        "example": (
                            "1. Cook pasta al dente\n"
                            "2. Mix eggs with cheese\n"
                            "3. Combine hot pasta with egg mixture"
                        ),
                    },
                    "time_minutes": {
                        "type": "integer",
                        "description": "Total cooking time in minutes",
                        "example": 30,
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                        "description": "Recipe difficulty level",
                        "example": "medium",
                    },
                    "servings": {
                        "type": "integer",
                        "description": "Number of servings",
                        "example": 4,
                        "minimum": 1,
                    },
                    "is_public": {
                        "type": "boolean",
                        "description": "Whether recipe is publicly visible",
                        "example": True,
                    },
                    "tag_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of tag names "
                            "(created automatically if they don't exist)"
                        ),
                        "example": ["italian", "pasta", "dinner"],
                    },
                    "recipe_ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ingredient_name": {
                                    "type": "string",
                                    "description": "Name of the ingredient",
                                    "example": "spaghetti",
                                },
                                "quantity": {
                                    "type": "string",
                                    "description": "Amount needed",
                                    "example": "400g",
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Optional preparation notes",
                                    "example": "preferably bronze-die cut",
                                },
                            },
                            "required": ["ingredient_name", "quantity"],
                        },
                        "description": "List of recipe ingredients",
                        "example": [
                            {
                                "ingredient_name": "spaghetti",
                                "quantity": "400g",
                                "notes": "bronze-die cut",
                            },
                            {
                                "ingredient_name": "eggs",
                                "quantity": "3 large",
                                "notes": "room temperature",
                            },
                            {
                                "ingredient_name": "parmesan cheese",
                                "quantity": "100g",
                                "notes": "freshly grated",
                            },
                        ],
                    },
                },
                "required": [
                    "title",
                    "instructions",
                    "time_minutes",
                    "recipe_ingredients",
                ],
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Recipe title",
                        "example": "Homemade Pizza Margherita",
                    },
                    "description": {
                        "type": "string",
                        "description": "Recipe description",
                        "example": (
                            "Authentic Italian pizza with fresh tomatoes, mozzarella"
                        ),
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Cooking instructions",
                        "example": (
                            "1. Prepare pizza dough\n"
                            "2. Roll out thin\n"
                            "3. Add sauce and toppings\n"
                            "4. Bake at 250°C for 10-12 minutes"
                        ),
                    },
                    "time_minutes": {
                        "type": "integer",
                        "description": "Cooking time in minutes",
                        "example": 45,
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                        "example": "medium",
                    },
                    "servings": {
                        "type": "integer",
                        "description": "Number of servings",
                        "example": 4,
                        "minimum": 1,
                    },
                    "is_public": {
                        "type": "boolean",
                        "description": "Make recipe publicly visible",
                        "example": True,
                    },
                    "tag_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tag names as form array",
                        "example": ["italian", "pizza", "comfort-food"],
                    },
                    "recipe_ingredients_json": {
                        "type": "string",
                        "description": "JSON string containing ingredients array",
                        "example": (
                            '[{"ingredient_name":"pizza dough","quantity":"1 ball",'
                            '"notes":"homemade or store-bought"},'
                            '{"ingredient_name":"tomato sauce",'
                            '"quantity":"200ml","notes":""},'
                            '{"ingredient_name":"mozzarella cheese",'
                            '"quantity":"200g","notes":"fresh, sliced"},'
                            '{"ingredient_name":"fresh basil",'
                            '"quantity":"10 leaves","notes":""}]'
                        ),
                    },
                    "image": {
                        "type": "string",
                        "format": "binary",
                        "description": "Recipe image file",
                    },
                },
                "required": [
                    "title",
                    "instructions",
                    "time_minutes",
                    "recipe_ingredients_json",
                ],
            },
        },
    ),
    retrieve=extend_schema(
        summary="Get recipe details",
        description="View complete recipe information.",
    ),
    partial_update=extend_schema(
        summary="Update your recipe",
        description="Update your own recipe. Only recipe owners can make changes.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Recipe title",
                        "example": "Chocolate Chip Cookies",
                    },
                    "description": {
                        "type": "string",
                        "description": "Recipe description",
                        "example": "Soft homemade cookies with chocolate chips",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Cooking instructions",
                        "example": (
                            "1. Mix dry ingredients\n"
                            "2. Cream butter and sugars\n"
                            "3. Add eggs and vanilla\n"
                            "4. Combine wet and dry ingredients\n"
                            "5. Fold in chocolate chips\n"
                            "6. Bake at 180°C for 10-12 minutes"
                        ),
                    },
                    "time_minutes": {
                        "type": "integer",
                        "description": "Cooking time in minutes",
                        "example": 25,
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                        "example": "easy",
                    },
                    "servings": {
                        "type": "integer",
                        "description": "Number of servings",
                        "example": 24,
                        "minimum": 1,
                    },
                    "is_public": {
                        "type": "boolean",
                        "description": "Public visibility",
                        "example": True,
                    },
                    "tag_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Update recipe tags",
                        "example": ["dessert", "cookies", "baking"],
                    },
                    "recipe_ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ingredient_name": {
                                    "type": "string",
                                    "example": "flour",
                                },
                                "quantity": {
                                    "type": "string",
                                    "example": "2 cups",
                                },
                                "notes": {
                                    "type": "string",
                                    "example": "all-purpose",
                                },
                            },
                            "required": ["ingredient_name", "quantity"],
                        },
                        "description": "Update recipe ingredients",
                        "example": [
                            {
                                "ingredient_name": "flour",
                                "quantity": "2 cups",
                                "notes": "all-purpose",
                            },
                            {
                                "ingredient_name": "butter",
                                "quantity": "1 cup",
                                "notes": "softened",
                            },
                            {
                                "ingredient_name": "brown sugar",
                                "quantity": "3/4 cup",
                                "notes": "",
                            },
                            {
                                "ingredient_name": "chocolate chips",
                                "quantity": "2 cups",
                                "notes": "semi-sweet",
                            },
                        ],
                    },
                },
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Recipe title",
                        "example": "Grilled Chicken Salad",
                    },
                    "description": {
                        "type": "string",
                        "description": "Recipe description",
                        "example": (
                            "Healthy and fresh salad with grilled chicken"
                        ),
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Cooking instructions",
                        "example": (
                            "1. Season and grill chicken breast\n"
                            "2. Prepare mixed greens\n"
                            "3. Make vinaigrette\n"
                            "4. Slice chicken and assemble salad"
                        ),
                    },
                    "time_minutes": {
                        "type": "integer",
                        "description": "Cooking time in minutes",
                        "example": 20,
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                        "example": "easy",
                    },
                    "servings": {
                        "type": "integer",
                        "description": "Number of servings",
                        "example": 2,
                        "minimum": 1,
                    },
                    "is_public": {
                        "type": "boolean",
                        "description": "Public visibility",
                        "example": True,
                    },
                    "tag_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tag names as form array",
                        "example": ["healthy", "salad", "protein"],
                    },
                    "recipe_ingredients_json": {
                        "type": "string",
                        "description": (
                            "JSON string of ingredients for multipart uploads"
                        ),
                        "example": (
                            '[{"ingredient_name":"chicken breast","quantity":"2 pieces",'
                            '"notes":"boneless, skinless"},'
                            '{"ingredient_name":"mixed greens","quantity":"4 cups",'
                            '"notes":""},'
                            '{"ingredient_name":"cherry tomatoes","quantity":"1 cup",'
                            '"notes":"halved"}]'
                        ),
                    },
                    "image": {
                        "type": "string",
                        "format": "binary",
                        "description": "New recipe image",
                    },
                },
            },
        },
    ),
    destroy=extend_schema(
        summary="Delete your recipe",
        description="Permanently delete your own recipe. This action cannot be undone.",
    ),
)
