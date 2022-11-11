from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from recipes.models import Ingredient, Favorite, Recipe, ShoppingList, Tag

from .filters import IngredientSearchFilter, RecipeFilter
from .paginations import CustomPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (IngredientSerializer, RecipeSerializer,
                          FavoriteSerializer, RecipeListSerializer,
                          ShoppingListSerializer, TagSerializer)


class TagsViewSet(ReadOnlyModelViewSet):
    """Вьюсет для тегов, добавить тег может только администратор."""

    queryset = Tag.objects.all()
    permission_classes = AllowAny,
    serializer_class = TagSerializer


class IngredientsViewSet(ReadOnlyModelViewSet):
    """Вьюсет для ингредиентов. Добавить ингредиенты может только
    администратор."""

    queryset = Ingredient.objects.all()
    permission_classes = AllowAny,
    serializer_class = IngredientSerializer
    filter_backends = [IngredientSearchFilter]
    search_fields = '^name',


class RecipesViewSet(ModelViewSet):
    """Вьюсет для рецептов. Анонимным пользователям разрешено только
    просматривать рецепты."""

    queryset = Recipe.objects.all()
    permission_classes = IsAuthorOrReadOnly,
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.action in ('retrieve', 'list'):
            return RecipeListSerializer
        return RecipeSerializer

    @staticmethod
    def post_method_for_actions(request, pk, serializers):
        data = {'user': request.user.id, 'recipe': pk}
        serializer = serializers(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_method_for_actions(request, model, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        obj = get_object_or_404(model, user=request.user, recipe=recipe)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['POST'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        return self.post_method_for_actions(
            request=request,
            pk=pk,
            serializers=FavoriteSerializer
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        return self.delete_method_for_actions(
            request=request,
            model=Favorite,
            pk=pk
        )

    @action(
        detail=True,
        methods=['POST'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_list(self, request, pk):
        return self.post_method_for_actions(
            request=request,
            pk=pk,
            serializers=ShoppingListSerializer
        )

    @shopping_list.mapping.delete
    def delete_favorite(self, request, pk):
        return self.delete_method_for_actions(
            request=request,
            model=ShoppingList,
            pk=pk
        )
