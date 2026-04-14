from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GroceryList, Recipe
from .serializers import (
    LoginSerializer,
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
