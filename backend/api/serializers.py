from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorite, Ingredient,  # isort:skip
                            IngredientAmount, Recipe,  # isort:skip
                            ShoppingCart, Tag)  # isort:skip
from users.models import Follow  # isort:skip

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    """Сериализатор описывающий пользователя."""

    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        """Функция возвращающая, подписан ли пользователь на автора
        рецепта или нет."""

        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(author=obj.id, user=user).exists()


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор описывающий регистрацию пользователя."""

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
            'email',
        )
        extra_kwargs = {'password': {'write_only': True, 'min_length': 8}}

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class FollowSerializer(CustomUserSerializer):
    """Сериализатор описывающий подписки пользователя на авторов рецептов."""

    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()
        limit = request.query_params.get('recipes_limit')
        if limit:
            recipes = recipes[:int(limit)]
        return RecipeInfoSerializer(recipes, many=True).data

    @staticmethod
    def get_recipes_count(obj):
        return obj.recipes.count()


class RecipeInfoSerializer(serializers.ModelSerializer):
    """Сериализатор с краткой информацией о рецепте."""

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор описывающий тег."""

    class Meta:
        model = Tag
        fields = '__all__'
        read_only_fields = '__all__',


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор описывающий ингредиент."""

    class Meta:
        model = Ingredient
        fields = '__all__'
        read_only_fields = '__all__',


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор описывающий количество ингредиента."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientAmount
        fields = 'id', 'name', 'measurement_unit', 'amount',


class AddIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления ингредиентов."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientAmount
        fields = 'id', 'amount',


class RecipeListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка рецептов."""

    tags = TagSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField(read_only=True)
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    @staticmethod
    def get_ingredients(obj):
        queryset = IngredientAmount.objects.filter(recipe=obj)
        return IngredientAmountSerializer(queryset, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(recipe=obj, user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            recipe=obj,
            user=request.user
        ).exists()


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления и обновления рецепта."""

    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField()
    ingredients = AddIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'author', 'text', 'image', 'ingredients', 'tags',
            'cooking_time'
        )

    @staticmethod
    def __check_len(name, lst):
        value = {'tags': 'Теги', 'ingredients': 'Ингредиенты'}
        if len(set(lst)) < len(lst):
            raise serializers.ValidationError(
                {'name': f'{value[name]} должны быть уникальными.'}
            )

    def tags_validation(self, tags):
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Выберите хотя бы один тег.'}
            )
        self.__check_len('tags', tags)

    def ingredient_validation(self, ingredients):
        ingredients_id = [i['id'] for i in ingredients]
        self.__check_len('ingredients', ingredients_id)
        if any([int(i['amount']) <= 0 for i in ingredients]):
            raise serializers.ValidationError(
                {'amount': 'Количество ингредиента должно быть больше 0.'}
            )

    @staticmethod
    def cooking_time_validation(cooking_time):
        if int(cooking_time) <= 0:
            raise serializers.ValidationError(
                {'cooking_time': 'Время приготовления должно быть больше 0.'}
            )

    def validate(self, data):
        self.tags_validation(data['tags'])
        self.ingredient_validation(data['ingredients'])
        self.cooking_time_validation(data['cooking_time'])
        return data

    @staticmethod
    def create_ingredients(recipe, ingredients):
        ingredients_list = [IngredientAmount(
            recipe=recipe,
            ingredient=ing['id'],
            amount=ing['amount']
        ) for ing in ingredients]
        IngredientAmount.objects.bulk_create(ingredients_list)

    def create(self, validated_data):
        author = self.context.get('request').user
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.save()
        recipe.tags.set(tags_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, recipe, validated_data):
        recipe.tags.clear()
        IngredientAmount.objects.filter(recipe=recipe).delete()
        recipe.tags.set(validated_data.pop('tags'))
        self.create_ingredients(recipe, validated_data.pop('ingredients'))
        return super().update(recipe, validated_data)

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return RecipeListSerializer(instance, context=context).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""

    class Meta:
        model = ShoppingCart
        fields = 'recipe', 'user',
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в список покупок.'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeInfoSerializer(
            instance.recipe,
            context={'request': request}
        ).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""

    class Meta:
        model = Favorite
        fields = 'user', 'recipe',
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в избранное.'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeInfoSerializer(
            instance.recipe,
            context={'request': request}
        ).data
