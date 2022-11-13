from django_filters.rest_framework import FilterSet, filters
from rest_framework.filters import SearchFilter

from recipes.models import Recipe


class RecipeFilter(FilterSet):
    """Фильтры по тегам для рецептов."""

    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')
    is_favorite = filters.BooleanFilter(method='filter_is_favorite')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = (
            'author',
            'tags',
            'is_favorite',
            'is_in_shopping_cart',
        )

    def filter_is_favorite(self, queryset, name, value):
        """Фильтр по избранным рецептам."""

        if value:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_shopping_cart(self, queryset, name, value):
        """Фильтр по спискам покупок."""

        if value:
            return queryset.filter(lists_user=self.request.user)
        return queryset


class IngredientSearchFilter(SearchFilter):
    """Фильтр для поиска ингредиента по наименованию."""

    search_param = 'name'
