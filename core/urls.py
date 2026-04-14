from django.urls import path

from .views import (
    GroceryListRecipeMatchAPIView,
    LoginAPIView,
    LogoutAPIView,
    RecipeDetailAPIView,
    RecipeListAPIView,
    SignUpAPIView,
)

urlpatterns = [
    path("auth/signup/", SignUpAPIView.as_view(), name="signup"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("recipes/", RecipeListAPIView.as_view(), name="recipe-list"),
    path("recipes/<int:pk>/", RecipeDetailAPIView.as_view(), name="recipe-detail"),
    path(
        "grocery-lists/<int:grocery_list_id>/matching-recipes/",
        GroceryListRecipeMatchAPIView.as_view(),
        name="grocery-list-recipe-matches",
    ),
]
