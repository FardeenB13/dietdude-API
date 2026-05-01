from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from google import genai

from .grocery_mapping import sync_grocery_items_from_text
from .models import GroceryList, Recipe
from .serializers import (
    AskGeminiSerializer,
    GroceryItemSerializer,
    LoginSerializer,
    PreferencesSerializer,
    GroceryListSerializer,
    RecipeDetailSerializer,
    RecipeListSerializer,
    RecipeMatchedDetailSerializer,
    SignUpSerializer,
    UserSerializer,
)


def matching_recipes_queryset(ingredient_ids):
    """Recipes the user can cook if they have every ingredient in ``ingredient_ids``."""
    ingredient_ids = list(ingredient_ids)
    if not ingredient_ids:
        return Recipe.objects.none()
    return (
        Recipe.objects.annotate(
            total_ingredients=Count("recipeingredient", distinct=True),
            matched_ingredients=Count(
                "recipeingredient",
                filter=Q(recipeingredient__ingredient_id__in=ingredient_ids),
                distinct=True,
            ),
        )
        .filter(total_ingredients__gt=0, matched_ingredients__gte=1)
        .filter(matched_ingredients=F("total_ingredients"))
        .order_by("name")
    )


class RecipeListAPIView(generics.ListAPIView):
    serializer_class = RecipeListSerializer

    def get_queryset(self):
        queryset = Recipe.objects.all().order_by("name")

        max_cooking_time = self.request.query_params.get("max_cooking_time")
        servings = self.request.query_params.get("servings")
        ingredient = self.request.query_params.get("ingredient")
        search = self.request.query_params.get("search")

        if max_cooking_time:
            queryset = queryset.filter(cooking_time__lte=max_cooking_time)

        if servings:
            queryset = queryset.filter(servings=servings)

        if ingredient:
            queryset = queryset.filter(
                ingredients__name__icontains=ingredient
            ).distinct()

        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset


class RecipeDetailAPIView(generics.RetrieveAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeDetailSerializer


class GroceryListRecipeMatchAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RecipeMatchedDetailSerializer

    def get_queryset(self):
        grocery_list = get_object_or_404(
            GroceryList.objects.filter(user=self.request.user).prefetch_related("items"),
            pk=self.kwargs["grocery_list_id"],
        )
        grocery_ingredient_ids = grocery_list.items.values_list("ingredient_id", flat=True)
        return matching_recipes_queryset(grocery_ingredient_ids).prefetch_related(
            "recipeingredient_set__ingredient"
        )


class LatestGroceryListMatchingRecipesAPIView(generics.ListAPIView):
    """Matching recipes for the user's most recent grocery list (frontend-friendly)."""

    permission_classes = [IsAuthenticated]
    serializer_class = RecipeMatchedDetailSerializer

    def list(self, request, *args, **kwargs):
        has_list = GroceryList.objects.filter(user=request.user).exists()
        if not has_list:
            return Response(
                {"detail": "No grocery list found yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        grocery_list = (
            GroceryList.objects.filter(user=self.request.user)
            .prefetch_related("items")
            .order_by("-created_at")
            .first()
        )
        if not grocery_list:
            return Recipe.objects.none()
        ids = grocery_list.items.values_list("ingredient_id", flat=True)
        return matching_recipes_queryset(ids).prefetch_related(
            "recipeingredient_set__ingredient"
        )


class SignUpAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class AskGeminiAPIView(APIView):
    """POST a natural-language question; response text comes from Gemini."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AskGeminiSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return Response(
                {"detail": "GEMINI_API_KEY is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user = request.user
        contents = (
            "You are DietDude, a concise assistant for groceries, cooking, nutrition, and meal planning. "
            "If you are unsure, say so. Do not invent medical facts.\n\n"
            f"User diet preference (code): {user.diet}.\n\n"
            f"User question:\n{question}"
        )

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=contents,
            )
            answer = response.text if getattr(response, "text", None) else ""
            if not answer.strip():
                return Response(
                    {"detail": "The model returned an empty response."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            return Response({"answer": answer}, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response(
                {"detail": f"Failed to get answer: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdatePreferencesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = PreferencesSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

class GenerateGroceryListAPIView(APIView):
    """
    Gemini generates grocery text; mapped rows link to DB ingredients; response includes
    ``matching_recipes`` you can cook with those ingredients. For ad‑hoc Q&A use ``POST /ai/ask/``.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return Response(
                {"detail": "GEMINI_API_KEY is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user = request.user

        prompt = f"""
Create a grocery list for ONE shopping trip using these saved user preferences.

Diet: {user.diet}
Budget per trip: ${user.budget}
Shopping frequency: every {user.shopping_frequency_value} {user.shopping_frequency_unit}

Requirements:
- Make the grocery list suitable for the selected diet.
- Keep the list realistic for the budget.
- Group items into:
  1. Produce
  2. Protein
  3. Dairy / Alternatives
  4. Grains / Pantry
  5. Snacks
  6. Miscellaneous
- Include rough quantities.
- Keep it clean and easy to read.
- Prefer clear, standard ingredient names (e.g. Chicken Breast, Rice, Broccoli, Eggs) so items map to a recipe database.
- End with: Estimated total: $X-$Y
- Do not include extra explanation.
"""

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
            )

            grocery_text = response.text if getattr(response, "text", None) else "Unable to generate grocery list."

            grocery_list = GroceryList.objects.create(
                user=user,
                raw_text=grocery_text,
            )
            mapped_count = sync_grocery_items_from_text(grocery_list)

            grocery_list = (
                GroceryList.objects.prefetch_related("items__ingredient")
                .get(pk=grocery_list.pk)
            )
            ingredient_ids = list(
                grocery_list.items.values_list("ingredient_id", flat=True)
            )
            recipe_qs = matching_recipes_queryset(ingredient_ids).prefetch_related(
                "recipeingredient_set__ingredient"
            )

            return Response(
                {
                    "grocery_list": grocery_text,
                    "grocery_list_id": grocery_list.id,
                    "created_at": grocery_list.created_at,
                    "mapped_ingredient_count": mapped_count,
                    "items": GroceryItemSerializer(
                        grocery_list.items.all(),
                        many=True,
                    ).data,
                    "matching_recipes": RecipeMatchedDetailSerializer(
                        recipe_qs,
                        many=True,
                    ).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Failed to generate grocery list: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GroceryListMapItemsAPIView(APIView):
    """Parse raw_text and attach matching Ingredient rows as GroceryItem (for recipe matching)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, grocery_list_id):
        grocery_list = get_object_or_404(
            GroceryList.objects.filter(user=request.user), pk=grocery_list_id
        )
        created = sync_grocery_items_from_text(grocery_list)
        return Response(
            {
                "grocery_list_id": grocery_list.id,
                "new_items_created": created,
                "total_items": grocery_list.items.count(),
            },
            status=status.HTTP_200_OK,
        )


class LatestGroceryListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grocery_list = (
            GroceryList.objects.filter(user=request.user)
            .prefetch_related("items__ingredient")
            .order_by("-created_at")
            .first()
        )

        if not grocery_list:
            return Response(
                {"detail": "No grocery list found yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = GroceryListSerializer(grocery_list)
        return Response(serializer.data, status=status.HTTP_200_OK)
