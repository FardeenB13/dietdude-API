from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie

from .views import (
    AskGeminiAPIView,
    GenerateGroceryListAPIView,
    GroceryListMapItemsAPIView,
    GroceryListRecipeMatchAPIView,
    LatestGroceryListAPIView,
    LatestGroceryListMatchingRecipesAPIView,
    LoginAPIView,
    LogoutAPIView,
    RecipeDetailAPIView,
    RecipeListAPIView,
    SignUpAPIView,
    UpdatePreferencesAPIView,
)

@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})

urlpatterns = [
    path("auth/signup/", SignUpAPIView.as_view(), name="signup"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("csrf/", csrf, name="csrf"),
    path("recipes/", RecipeListAPIView.as_view(), name="recipe-list"),
    path("recipes/<int:pk>/", RecipeDetailAPIView.as_view(), name="recipe-detail"),
    path("user/preferences/", UpdatePreferencesAPIView.as_view(), name="update-preferences"),
    path("ai/ask/", AskGeminiAPIView.as_view(), name="ai-ask"),
    path("grocery-list/generate/", GenerateGroceryListAPIView.as_view(), name="generate-grocery-list"),
    path("grocery-list/latest/", LatestGroceryListAPIView.as_view(), name="latest-grocery-list"),
    path(
        "grocery-list/latest/matching-recipes/",
        LatestGroceryListMatchingRecipesAPIView.as_view(),
        name="latest-grocery-list-matching-recipes",
    ),
    path(
        "grocery-lists/<int:grocery_list_id>/map-items/",
        GroceryListMapItemsAPIView.as_view(),
        name="grocery-list-map-items",
    ),
    path(
        "grocery-lists/<int:grocery_list_id>/matching-recipes/",
        GroceryListRecipeMatchAPIView.as_view(),
        name="grocery-list-recipe-matches",
    ),
]
