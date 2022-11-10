from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Ingredient, IngredientAmount, Favorite, Recipe,
                            ShoppingList, Tag)

from users.models import Follow


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
    amount_recipes = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
            'email',
            'subscribed',
            'recipes',
            'amount_recipes',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()
        limit = request.query_param.get('recipes_limit')
        if limit:
            recipes = recipes[:int(limit)]
        return RecipeInfoSerializer(recipes, many=True).data


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
        fields = 'id', 'name', 'amount', 'measurement_unit'


class AddIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления ингредиентов."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientAmount
        fields = 'id', 'amount',


class RecipeListSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения рецептов."""

    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(read_only=True, many=True)
    ingredients = serializers.SerializerMethodField(read_only=True)
    is_favorite = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_list = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = '__all__'

    @staticmethod
    def get_ingredients(obj):
        queryset = IngredientAmount.objects.filter(recipe=obj)
        return IngredientAmountSerializer(queryset, many=True).data

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(recipe=obj, user=request.user).data

    def get_is_in_shopping_list(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingList.objects.filter(
            recipe=obj,
            user=request.user
        ).data


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления и обновления рецептов."""

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

    def validate(self, data):
        tags, tags_list, ingredients_list = data['tags'], [], []
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Выберите хотя бы один тег.'}
            )
        for tag in tags:
            if tag is tags_list:
                raise serializers.ValidationError(
                    {'tags': 'Теги должны быть уникальными.'}
                )
            tags_list.append(tag)
        for ingredient in data['ingredients']:
            if ingredient['id'] in ingredients_list:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты должны быть уникальны.'}
                )
            ingredients_list.append(ingredient['id'])
            if int(ingredient['amount']) <= 0:
                raise serializers.ValidationError(
                    {'amount': 'Количество ингредиента должно быть больше 0.'}
                )
        if int(data['cooking_time']) <= 0:
            raise serializers.ValidationError(
                {'cooking_time': 'Время приготовления должно быть больше 0.'}
            )

    @staticmethod
    def create_ingredients(recipe, ingredients):
        bulk_list = [IngredientAmount(
            recipe=recipe,
            ingredient=ing['id'],
            amount=ing['amount']
        ) for ing in ingredients]
        IngredientAmount.objects.bulk_create(bulk_list)

    @staticmethod
    def create_tags(recipe, tags):
        for tag in tags:
            recipe.tags.add(tag)

    def create(self, validated_data):
        author = self.context.get('request').user
        recipe = Recipe.objects.create(author=author, **validated_data)
        self.create_tags(recipe, validated_data.pop('tags'))
        self.create_ingredients(recipe, validated_data.pop('ingredients'))
        return recipe

    def update(self, recipe, validated_data):
        recipe.tags.clear()
        IngredientAmount.objects.filter(recipe=recipe).delete()
        self.create_tags(recipe, validated_data.pop('tags'))
        self.create_ingredients(recipe, validated_data.pop('ingredients'))
        return super().update(recipe, validated_data)

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return RecipeListSerializer(instance, context=context).data


class ShoppingListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""

    class Meta:
        model = ShoppingList
        fields = 'recipe', 'user',

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
        fields = 'users', 'recipe',

    def validate(self, data):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        if Favorite.objects.filter(
            user=request.user,
            recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError(
                {'status': 'Рецепт уже добавлен в избранное.'}
            )
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeInfoSerializer(
            instance.recipe,
            context={'request': request}
        ).data
