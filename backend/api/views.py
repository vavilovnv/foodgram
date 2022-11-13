from datetime import date

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (Favorite, Ingredient, IngredientAmount, Recipe,
                            ShoppingCart, Tag)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .filters import IngredientSearchFilter, RecipeFilter
from .paginations import CustomPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          RecipeListSerializer, RecipeSerializer,
                          ShoppingCartSerializer, TagSerializer)


class TagsViewSet(ReadOnlyModelViewSet):
    """Вьюсет для тегов, добавить тег может только администратор."""

    queryset = Tag.objects.all()
    permission_classes = AllowAny,
    serializer_class = TagSerializer
    pagination_class = None


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
    def post_method(request, pk, serializers):
        data = {'user': request.user.id, 'recipe': pk}
        serializer = serializers(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_method(request, model, pk):
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
        return self.post_method(
            request=request,
            pk=pk,
            serializers=FavoriteSerializer
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        return self.delete_method(
            request=request,
            model=Favorite,
            pk=pk
        )

    @action(
        detail=True,
        methods=['POST'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        return self.post_method(
            request=request,
            pk=pk,
            serializers=ShoppingCartSerializer
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        return self.delete_method(
            request=request,
            model=ShoppingCart,
            pk=pk
        )

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        height_page, string_interval, text_indent = 750, 15, 100
        fonts_size = {
            'small': 10,
            'normal': 12,
            'huge': 18
        }
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = (
            'attachment;',
            'filename="shopping_list.pdf"'
        )
        pdfmetrics.registerFont(
            TTFont('arial', '../data/arial.ttf', 'UTF-8')
        )
        page = canvas.Canvas(response)
        page.setFont('arial', fonts_size['huge'])
        page.drawString(
            text_indent - 30,
            height_page,
            'Список ингредиентов для покупки:'
        )
        height_page -= string_interval * 2
        page.setFont('arial', size=fonts_size['normal'])
        ingredients = IngredientAmount.objects.filter(
            recipe__shopping_carts__user=request.user
        ).values_list(
            'ingredient__name',
            'ingredient__measurement_unit',
            'amount'
        )
        cart_list = {}
        for ingredient in ingredients:
            name, measure, amount = ingredient
            name = name.capitalize()
            if name in cart_list:
                cart_list[name]['amount'] += amount
            else:
                cart_list[name] = {
                    'unit': measure,
                    'amount': amount
                }
        for idx, (name, data) in enumerate(cart_list.items(), 1):
            description = f'{idx}. {name} ({data["unit"]}) - {data["amount"]}'
            page.drawString(text_indent, height_page, description)
            height_page -= string_interval
        page.setLineWidth(1)
        page.line(
            text_indent,
            height_page + 10,
            text_indent + 150,
            height_page + 10
        )
        page.setFont('arial', fonts_size['small'])
        page.drawString(
            text_indent,
            height_page,
            f'{date.today()} Foodgram project (c)'
        )
        page.showPage()
        page.save()
        return response
