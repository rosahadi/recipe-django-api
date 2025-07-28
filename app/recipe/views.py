from rest_framework import viewsets, filters, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
    ParseError,
)
from django.db.models import Q
from django.db import transaction, IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
import logging

from core.models import Recipe, Tag, Ingredient
from .serializers import (
    RecipeSerializer,
    RecipeListSerializer,
    TagSerializer,
    IngredientSerializer,
)
from .schemas import (
    tag_viewset_schema,
    ingredient_viewset_schema,
    recipe_viewset_schema,
)

logger = logging.getLogger(__name__)


class APIErrorHandler:
    """Centralized error handling for consistent API responses."""

    @staticmethod
    def handle_validation_error(e, context="operation"):
        """Handle DRF validation errors with detailed field-level feedback."""
        if hasattr(e, "detail") and isinstance(e.detail, dict):
            # Field-specific validation errors
            errors = {}
            for field, messages in e.detail.items():
                if isinstance(messages, list):
                    errors[field] = [str(msg) for msg in messages]
                else:
                    errors[field] = [str(messages)]

            return Response(
                {
                    "error": "validation_failed",
                    "message": f"Please correct the following errors in your {context}",
                    "field_errors": errors,
                    "status": "error",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            # General validation error
            return Response(
                {
                    "error": "validation_failed",
                    "message": (
                        str(e.detail) if hasattr(e, "detail") else str(e)
                    ),
                    "status": "error",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def handle_permission_error(user_email, action, resource="resource"):
        """Handle permission denied errors."""
        return Response(
            {
                "error": "permission_denied",
                "message": f"You don't have permission to {action} this {resource}",
                "status": "error",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    @staticmethod
    def handle_not_found_error(resource="Resource"):
        """Handle not found errors."""
        return Response(
            {
                "error": "not_found",
                "message": f"{resource} not found",
                "details": (
                    "The requested item doesn't exist or "
                    "you don't have access to it"
                ),
                "status": "error",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    @staticmethod
    def handle_authentication_error():
        """Handle authentication errors."""
        return Response(
            {
                "error": "authentication_required",
                "message": "Authentication is required for this action",
                "details": "Please log in and try again",
                "status": "error",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    @staticmethod
    def handle_parse_error(e):
        """Handle JSON/data parsing errors."""
        return Response(
            {
                "error": "invalid_request_format",
                "message": "Invalid request data format",
                "status": "error",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def handle_database_error(e, action="operation"):
        """Handle database-related errors."""
        if isinstance(e, IntegrityError):
            return Response(
                {
                    "error": "data_conflict",
                    "message": f"Data conflict occurred during {action}",
                    "details": (
                        "This might be due to duplicate data "
                        "or constraint violations"
                    ),
                    "status": "error",
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "error": "database_error",
                "message": f"Database error occurred during {action}",
                "details": "Please try again or contact us if the problem persists",
                "status": "error",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @staticmethod
    def handle_generic_error(e, action="operation"):
        """Handle unexpected errors."""
        logger.error(f"Unexpected error during {action}: {str(e)}")
        return Response(
            {
                "error": "internal_server_error",
                "message": f"An unexpected error occurred during {action}",
                "details": "Please try again or contact us if the problem persists",
                "status": "error",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @staticmethod
    def success_response(data, message, status_code=status.HTTP_200_OK):
        """Standardized success response."""
        return Response(
            {"status": "success", "message": message, "data": data},
            status=status_code,
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Allow read access to everyone, write access only to object owners."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class IsSuperUserOrReadOnly(permissions.BasePermission):
    """Allow read access to everyone, write access only to superusers."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_superuser


@tag_viewset_schema
class TagViewSet(viewsets.ModelViewSet):
    """Tag management system with enhanced error handling."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsSuperUserOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "usage_count", "created_at"]
    ordering = ["name"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        """Filter tags based on usage if requested."""
        try:
            queryset = self.queryset
            if self.request.query_params.get("used_only", "").lower() == "true":
                queryset = queryset.filter(usage_count__gt=0)
            return queryset
        except Exception as e:
            logger.error(f"Error filtering tags: {str(e)}")
            raise ValidationError("Invalid filter parameters for tags")

    def list(self, request, *args, **kwargs):
        """List tags with error handling."""
        try:
            response = super().list(request, *args, **kwargs)
            return response
        except ValidationError as e:
            return APIErrorHandler.handle_validation_error(e, "tag filtering")
        except Exception as e:
            return APIErrorHandler.handle_generic_error(e, "retrieving tags")

    def create(self, request, *args, **kwargs):
        """Create a new tag with enhanced error handling."""
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return APIErrorHandler.handle_validation_error(
                    ValidationError(serializer.errors), "tag creation"
                )

            self.perform_create(serializer)
            logger.info(
                f"Tag '{serializer.data.get('name')}' created by {request.user.email}"
            )

            return APIErrorHandler.success_response(
                serializer.data,
                f"Tag '{serializer.data.get('name')}' created successfully",
                status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return APIErrorHandler.handle_validation_error(e, "tag creation")
        except IntegrityError as e:
            return APIErrorHandler.handle_database_error(e, "tag creation")
        except Exception as e:
            return APIErrorHandler.handle_generic_error(e, "tag creation")


@ingredient_viewset_schema
class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Ingredient browsing system with enhanced error handling."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "category"]
    ordering_fields = ["name", "usage_count", "created_at"]
    ordering = ["name"]
    filterset_fields = ["category"]

    def get_queryset(self):
        """Filter ingredients based on usage."""
        try:
            queryset = self.queryset
            if self.request.query_params.get("used_only", "").lower() == "true":
                queryset = queryset.filter(usage_count__gt=0)
            return queryset
        except Exception as e:
            logger.error(f"Error filtering ingredients: {str(e)}")
            raise ValidationError("Invalid filter parameters for ingredients")

    def list(self, request, *args, **kwargs):
        """List ingredients with error handling."""
        try:
            response = super().list(request, *args, **kwargs)
            return response
        except ValidationError as e:
            return APIErrorHandler.handle_validation_error(
                e, "ingredient filtering"
            )
        except Exception as e:
            return APIErrorHandler.handle_generic_error(
                e, "retrieving ingredients"
            )


@recipe_viewset_schema
class RecipeViewSet(viewsets.ModelViewSet):
    """Recipe management system."""

    queryset = Recipe.objects.select_related("user").prefetch_related(
        "tags", "recipe_ingredients__ingredient"
    )
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["title", "description", "instructions"]
    ordering_fields = [
        "title",
        "time_minutes",
        "difficulty",
        "servings",
        "created_at",
    ]
    ordering = ["-created_at"]
    filterset_fields = ["difficulty", "servings", "is_public"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        """Filter recipes based on user permissions and query parameters."""
        queryset = self.queryset
        user = getattr(self.request, "user", None)

        # Apply basic permission filtering first
        if user and user.is_authenticated:
            if hasattr(user, "is_superuser") and user.is_superuser:
                # Superusers see everything
                pass
            else:
                # Regular authenticated users see public recipes + their own
                queryset = queryset.filter(Q(is_public=True) | Q(user=user))
        else:
            # Anonymous users or None user only see public recipes
            queryset = queryset.filter(is_public=True)

        # Apply additional filters
        try:
            params = self.request.query_params
            if params:
                queryset = self._apply_filters(queryset, params, user)
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_queryset: {str(e)}", exc_info=True
            )
            pass

        return queryset

    def _apply_filters(self, queryset, params, user):
        """Apply query parameter filters with validation."""
        try:
            # My recipes filter - only for authenticated users
            my_recipes = params.get("my_recipes", "").lower()
            if my_recipes == "true":
                if not user or not user.is_authenticated:
                    raise ValidationError(
                        "Authentication required for 'my_recipes' filter"
                    )
                queryset = queryset.filter(user=user)

            # User ID filter
            user_id = params.get("user_id")
            if user_id:
                try:
                    user_id = int(user_id)
                    if user_id <= 0:
                        raise ValidationError(
                            "Invalid user_id: " "must be a positive number"
                        )

                    if (
                        user
                        and user.is_authenticated
                        and hasattr(user, "is_superuser")
                        and user.is_superuser
                    ):
                        queryset = queryset.filter(user_id=user_id)
                    else:
                        queryset = queryset.filter(
                            user_id=user_id, is_public=True
                        )
                except (ValueError, TypeError):
                    raise ValidationError(
                        "Invalid user_id: must be a valid number"
                    )

            # Tag filter
            tags = params.get("tags")
            if tags and tags.strip():
                tag_names = [
                    tag.strip().lower()
                    for tag in tags.split(",")
                    if tag.strip()
                ]
                if tag_names:
                    queryset = queryset.filter(
                        tags__name__in=tag_names
                    ).distinct()

            # Ingredient filter
            ingredients = params.get("ingredients")
            if ingredients and ingredients.strip():
                ingredient_names = [
                    ing.strip().lower()
                    for ing in ingredients.split(",")
                    if ing.strip()
                ]
                if ingredient_names:
                    queryset = queryset.filter(
                        recipe_ingredients__ingredient__name__in=ingredient_names
                    ).distinct()

            # Time filter
            max_time = params.get("max_time")
            if max_time and max_time.strip():
                try:
                    max_time_int = int(max_time)
                    if max_time_int < 0:
                        raise ValidationError(
                            "max_time must be a positive number"
                        )
                    queryset = queryset.filter(time_minutes__lte=max_time_int)
                except (ValueError, TypeError):
                    raise ValidationError("max_time must be a valid number")

            # Servings filter
            min_servings = params.get("min_servings")
            if min_servings and min_servings.strip():
                try:
                    min_servings_int = int(min_servings)
                    if min_servings_int < 1:
                        raise ValidationError("min_servings must be at least 1")
                    queryset = queryset.filter(servings__gte=min_servings_int)
                except (ValueError, TypeError):
                    raise ValidationError("min_servings must be a valid number")

            return queryset
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error applying filters: {str(e)}", exc_info=True
            )
            raise ValidationError("Invalid filter parameters")

    def get_serializer_class(self):
        """Use appropriate serializer based on the action."""
        if self.action == "list":
            return RecipeListSerializer
        return RecipeSerializer

    def list(self, request, *args, **kwargs):
        """List recipes with enhanced error handling."""
        try:
            response = super().list(request, *args, **kwargs)
            return response
        except ValidationError as e:
            return APIErrorHandler.handle_validation_error(
                e, "recipe filtering"
            )
        except Exception as e:
            return APIErrorHandler.handle_generic_error(e, "retrieving recipes")

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific recipe with error handling."""
        try:
            response = super().retrieve(request, *args, **kwargs)
            return response
        except Recipe.DoesNotExist:
            return APIErrorHandler.handle_not_found_error("Recipe")
        except PermissionDenied:
            return APIErrorHandler.handle_permission_error(
                getattr(request.user, "email", "anonymous"), "view", "recipe"
            )
        except Exception as e:
            return APIErrorHandler.handle_generic_error(e, "retrieving recipe")

    def create(self, request, *args, **kwargs):
        """Create a new recipe with comprehensive error handling."""
        if not request.user.is_authenticated:
            return APIErrorHandler.handle_authentication_error()

        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                if not serializer.is_valid():
                    return APIErrorHandler.handle_validation_error(
                        ValidationError(serializer.errors), "recipe creation"
                    )

                self.perform_create(serializer)
                logger.info(
                    f"Recipe '{serializer.data.get('title')}' "
                    f"created by {request.user.email}"
                )

                return APIErrorHandler.success_response(
                    serializer.data,
                    f"Recipe '{serializer.data.get('title')}' created successfully",
                    status.HTTP_201_CREATED,
                )
        except ValidationError as e:
            return APIErrorHandler.handle_validation_error(e, "recipe creation")
        except ParseError as e:
            return APIErrorHandler.handle_parse_error(e)
        except IntegrityError as e:
            return APIErrorHandler.handle_database_error(e, "recipe creation")
        except Exception as e:
            return APIErrorHandler.handle_generic_error(e, "recipe creation")

    def partial_update(self, request, *args, **kwargs):
        """Update a recipe with detailed error handling."""
        try:
            instance = self.get_object()

            if instance.user != request.user and not request.user.is_superuser:
                return APIErrorHandler.handle_permission_error(
                    request.user.email, "update", "recipe"
                )

            with transaction.atomic():
                serializer = self.get_serializer(
                    instance, data=request.data, partial=True
                )
                if not serializer.is_valid():
                    return APIErrorHandler.handle_validation_error(
                        ValidationError(serializer.errors), "recipe update"
                    )

                self.perform_update(serializer)
                logger.info(
                    f"Recipe '{instance.title}' updated by {request.user.email}"
                )

                return APIErrorHandler.success_response(
                    serializer.data,
                    f"Recipe '{instance.title}' updated successfully",
                )
        except Recipe.DoesNotExist:
            return APIErrorHandler.handle_not_found_error("Recipe")
        except ValidationError as e:
            return APIErrorHandler.handle_validation_error(e, "recipe update")
        except ParseError as e:
            return APIErrorHandler.handle_parse_error(e)
        except PermissionDenied:
            return APIErrorHandler.handle_permission_error(
                request.user.email, "update", "recipe"
            )
        except IntegrityError as e:
            return APIErrorHandler.handle_database_error(e, "recipe update")
        except Exception as e:
            return APIErrorHandler.handle_generic_error(e, "recipe update")

    def destroy(self, request, *args, **kwargs):
        """Delete a recipe with error handling."""
        try:
            instance = self.get_object()

            if instance.user != request.user and not request.user.is_superuser:
                return APIErrorHandler.handle_permission_error(
                    request.user.email, "delete", "recipe"
                )

            recipe_title = instance.title
            with transaction.atomic():
                self.perform_destroy(instance)

            logger.info(
                f"Recipe '{recipe_title}' deleted by {request.user.email}"
            )

            return Response(
                {
                    "status": "success",
                    "message": f"Recipe '{recipe_title}' deleted successfully",
                },
                status=status.HTTP_200_OK,
            )
        except Recipe.DoesNotExist:
            return APIErrorHandler.handle_not_found_error("Recipe")
        except PermissionDenied:
            return APIErrorHandler.handle_permission_error(
                request.user.email, "delete", "recipe"
            )
        except IntegrityError as e:
            return APIErrorHandler.handle_database_error(e, "recipe deletion")
        except Exception as e:
            return APIErrorHandler.handle_generic_error(e, "recipe deletion")

    def perform_create(self, serializer):
        """Set the current user as the recipe owner."""
        serializer.save(user=self.request.user)
