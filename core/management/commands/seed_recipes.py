import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Recipe, Ingredient, RecipeIngredient


class Command(BaseCommand):
    help = 'Seed recipes from JSON'

    def handle(self, *args, **kwargs):
        path = Path(settings.BASE_DIR) / 'core' / 'data' / 'recipes.json'
        with path.open(encoding='utf-8') as f:
            data = json.load(f)

        for r in data:
            recipe, created = Recipe.objects.get_or_create(
                name=r["name"],
                defaults={
                    "description": r["description"],
                    "instructions": r["instructions"],
                    "cooking_time": r["cooking_time"],
                    "servings": r["servings"]
                }
            )

            if not created:
                continue  # skip duplicates

            for ing in r["ingredients"]:
                ingredient, _ = Ingredient.objects.get_or_create(
                    name=ing["name"]
                )

                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    quantity=ing["quantity"],
                    unit=ing["unit"]
                )

        self.stdout.write(self.style.SUCCESS("Recipes seeded successfully!"))