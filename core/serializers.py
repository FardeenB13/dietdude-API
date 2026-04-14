from django.http import QueryDict
from rest_framework import serializers

from .models import Recipe, RecipeIngredient, User


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


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "diet",
            "budget",
            "shopping_frequency_value",
            "shopping_frequency_unit",
        ]


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
