from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from recipes.serializers import RecipeSerializer

from .models import Follow

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
        return Follow.objects.filter(autor=obj.id, user=user).exists()


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
        return RecipeSerializer(recipes, many=True).data
