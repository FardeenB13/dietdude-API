from django.contrib import admin

# Register your models here.
# core/admin.py

from django.contrib import admin
from .models import User, Recipe, Ingredient, RecipeIngredient, GroceryList, GroceryItem

admin.site.register(User)
admin.site.register(Recipe)
admin.site.register(Ingredient)
admin.site.register(RecipeIngredient)
admin.site.register(GroceryList)
admin.site.register(GroceryItem)