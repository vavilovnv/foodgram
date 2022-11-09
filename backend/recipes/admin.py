from django.contrib import admin

from .models import Ingredient, IngredientAmount, Favorite, Recipe, ShoppingList, Tag


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = 'id', 'name', 'measurement_unit',
    list_filter = 'name',
    search_fields = 'name',
    empty_value_display = 'пусто'


@admin.register(IngredientAmount)
class IngredientAmountAdmin(admin.ModelAdmin):
    list_display = 'id', 'ingredient', 'recipe', 'amount',
    empty_value_display = 'пусто'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = 'id', 'name', 'slug',
    empty_value_display = 'пусто'


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = 'id', 'name', 'author', 'amount_ingredients', 'amount_tags',
    list_filter = 'name', 'author', 'tags',
    search_fields = 'name',
    empty_value_display = 'пусто'

    @staticmethod
    def amount_ingredients(obj):
        return '\n'.join(list(obj.ingredients.values_list('name', flat=True)))

    @staticmethod
    def amount_tags(obj):
        return '\n'.join(list(obj.tags.values_list('name', flat=True)))


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = 'id', 'user', 'recipe',
    empty_value_display = 'пусто'


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = 'id', 'user', 'recipe',
    empty_value_display = 'пусто'
