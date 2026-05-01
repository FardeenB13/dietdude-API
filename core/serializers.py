from django.http import QueryDict
from rest_framework import serializers

from .models import GroceryItem, GroceryList, Recipe, RecipeIngredient, User


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient = serializers.CharField(source="ingredient.name")

    class Meta:
        model = RecipeIngredient
        fields = ["ingredient", "quantity", "unit"]


class RecipeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ["id", "name", "description", "cooking_time", "servings"]


class RecipeDetailSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        source="recipeingredient_set", many=True, read_only=True
    )

    class Meta:
        model = Recipe
        fields = [
            "id",
            "name",
            "description",
            "instructions",
            "cooking_time",
            "servings",
            "ingredients",
        ]

class RecipeMatchSerializer(serializers.ModelSerializer):
    matched_ingredients = serializers.IntegerField(read_only=True)
    total_ingredients = serializers.IntegerField(read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "name",
            "description",
            "cooking_time",
            "servings",
            "matched_ingredients",
            "total_ingredients",
        ]


class RecipeMatchedDetailSerializer(serializers.ModelSerializer):
    """Full recipe for UI cards: instructions, ingredients, plus match counts."""

    ingredients = RecipeIngredientSerializer(
        source="recipeingredient_set", many=True, read_only=True
    )
    matched_ingredients = serializers.IntegerField(read_only=True)
    total_ingredients = serializers.IntegerField(read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "name",
            "description",
            "instructions",
            "cooking_time",
            "servings",
            "ingredients",
            "matched_ingredients",
            "total_ingredients",
        ]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "diet",
            "dietary_restrictions",
            "budget",
            "shopping_frequency_value",
            "shopping_frequency_unit",
        ]
class PreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "diet",
            "dietary_restrictions",
            "budget",
            "shopping_frequency_value",
            "shopping_frequency_unit",
        ]
        extra_kwargs = {
            "diet": {"required": False},
            "budget": {"required": False},
            "shopping_frequency_value": {"required": False},
            "shopping_frequency_unit": {"required": False},
        }
    def validate_budget(self, value):
        if value < 0:
            raise serializers.ValidationError("Budget must be a positive number.")
        return value
 
    def validate_shopping_frequency_value(self, value):
        if value < 1:
            raise serializers.ValidationError("Shopping frequency must be at least 1.")
        return value
    
    VALID_DIETS = {"none", "vegetarian", "vegan", "halal", "keto"}

    def validate_dietary_restrictions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list.")

        for v in value:
            if v not in self.VALID_DIETS:
                raise serializers.ValidationError(f"Invalid diet: {v}")

        return value

class GroceryItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = GroceryItem
        fields = ["id", "ingredient_name", "quantity", "unit"]


class GroceryListSerializer(serializers.ModelSerializer):
    items = GroceryItemSerializer(many=True, read_only=True)

    class Meta:
        model = GroceryList
        fields = ["id", "created_at", "raw_text", "items"]    
class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8, required=False)

    _CAMELCASE_ALIASES = {
        "firstName": "first_name",
        "lastName": "last_name",
        "confirmPassword": "confirm_password",
    }

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
            "confirm_password",
            "diet",
            "budget",
            "shopping_frequency_value",
            "shopping_frequency_unit",
        ]

    def to_internal_value(self, data):
        # JSON is a dict; form / multipart is QueryDict — normalize so aliases apply.
        if isinstance(data, QueryDict):
            data = data.dict()
        elif not isinstance(data, dict):
            try:
                data = dict(data)
            except (TypeError, ValueError):
                return super().to_internal_value(data)

        data = {**data}
        for camel, snake in self._CAMELCASE_ALIASES.items():
            if camel in data and snake not in data:
                data[snake] = data.pop(camel)
        # Single password field in the UI: treat password as confirmation.
        pwd = data.get("password")
        if pwd and not data.get("confirm_password"):
            data["confirm_password"] = pwd

        return super().to_internal_value(data)

    def validate(self, attrs):
        confirm = attrs.get("confirm_password")
        if confirm is None:
            confirm = attrs["password"]
            attrs["confirm_password"] = confirm
        if attrs["password"] != confirm:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AskGeminiSerializer(serializers.Serializer):
    question = serializers.CharField(
        required=True,
        max_length=8000,
        trim_whitespace=True,
        allow_blank=False,
    )
