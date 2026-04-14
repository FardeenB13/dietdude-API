from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email")

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # Admin creation via `createsuperuser` does not prompt for profile
        # preferences, so provide safe defaults.
        extra_fields.setdefault('budget', 0)
        extra_fields.setdefault('shopping_frequency_value', 7)
        extra_fields.setdefault('shopping_frequency_unit', 'days')

        return self.create_user(email, first_name, last_name, password, **extra_fields)

class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    # Preferences
    DIET_CHOICES = [
        ('none', 'No Restriction'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('halal', 'Halal'),
        ('keto', 'Keto'),
    ]

    diet = models.CharField(max_length=20, choices=DIET_CHOICES, default='none')

    # ✅ NEW FIELDS
    budget = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    shopping_frequency_value = models.PositiveIntegerField(default=7)

    SHOP_FREQ_UNIT_CHOICES = [
        ('days', 'Days'),
        ('weeks', 'Weeks'),
    ]
    shopping_frequency_unit = models.CharField(
        max_length=10,
        choices=SHOP_FREQ_UNIT_CHOICES,
        default='days'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name
class Recipe(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField()
    cooking_time = models.IntegerField(help_text="Minutes")
    servings = models.IntegerField()

    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes'
    )

    def __str__(self):
        return self.name

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    quantity = models.FloatField()
    unit = models.CharField(max_length=50)  # e.g., cups, grams, etc.

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name} for {self.recipe.name}"
    
class GroceryList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grocery_lists')
    created_at = models.DateTimeField(auto_now_add=True)

    raw_text = models.TextField()  # store ChatGPT output

    def __str__(self):
        return f"Grocery List for {self.user.email} - {self.created_at}"
    
class GroceryItem(models.Model):
    grocery_list = models.ForeignKey(GroceryList, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    quantity = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.ingredient.name}"