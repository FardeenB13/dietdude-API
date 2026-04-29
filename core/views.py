from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from google import genai

from .models import GroceryList, Recipe
from .serializers import (
    LoginSerializer,
    PreferencesSerializer, 
    GroceryListSerializer,
    RecipeDetailSerializer,
    RecipeListSerializer,
    RecipeMatchSerializer,
    SignUpSerializer,
    UserSerializer,
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
    serializer_class = RecipeMatchSerializer

    def get_queryset(self):
        grocery_list = get_object_or_404(
            GroceryList.objects.prefetch_related("items"), pk=self.kwargs["grocery_list_id"]
        )
        grocery_ingredient_ids = grocery_list.items.values_list("ingredient_id", flat=True)

        # Return recipes whose every ingredient exists in this grocery list.
        return (
            Recipe.objects.annotate(
                total_ingredients=Count("recipeingredient", distinct=True),
                matched_ingredients=Count(
                    "recipeingredient",
                    filter=Q(recipeingredient__ingredient_id__in=grocery_ingredient_ids),
                    distinct=True,
                ),
            )
            .filter(total_ingredients__gt=0, matched_ingredients__gte=1)
            .filter(matched_ingredients=F("total_ingredients"))
            .order_by("name")
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

Dietary restrictions: {", ".join(user.dietary_restrictions) if user.dietary_restrictions else "none"}
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

            return Response(
                {
                    "grocery_list": grocery_text,
                    "grocery_list_id": grocery_list.id,
                    "created_at": grocery_list.created_at,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Failed to generate grocery list: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LatestGroceryListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grocery_list = (
            GroceryList.objects
            .filter(user=request.user)
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
