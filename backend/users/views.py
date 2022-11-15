from django.contrib.auth import get_user_model
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView

from api.paginations import CustomPageNumberPagination  # isort:skip
from api.serializers import (CustomUserSerializer,  # isort:skip
                             FollowSerializer)  # isort:skip

from .models import Follow  # isort:skip

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователем."""

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Запрос информации пользователя о себе."""

        context = {'request': request}
        serializer = CustomUserSerializer(request.user, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FollowViewSet(APIView):
    """Вьюсет для работы с подписками на автора."""

    serializer_class = FollowSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def post(self, request, *args, **kwargs):
        """Добавление подписки на автора."""

        self_user = request.user
        author_id = self.kwargs.get('user_id')
        author = get_object_or_404(User, id=author_id)
        if self_user.id == author_id:
            return Response(
                {'error': 'Нельзя подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        obj, created = Follow.objects.get_or_create(
            user=self_user,
            author_id=author_id
        )
        if not created:
            return Response(
                {'error': 'Подписка уже оформлена.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Follow.objects.create(user=self_user, author_id=author_id)
        context = {'request': request}
        return Response(
            self.serializer_class(author, context=context).data,
            status=status.HTTP_201_CREATED
        )

    def delete(self, request, *args, **kwargs):
        """Удаление подписки на автора."""

        self_user = request.user
        author_id = self.kwargs.get('user_id')
        get_object_or_404(User, id=author_id)
        subscribe = Follow.objects.filter(
            user=self_user,
            author_id=author_id
        )
        if subscribe:
            subscribe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Подписка на автора не оформлена.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class FollowListView(ListAPIView):
    """Класс для просмотра подписок."""

    serializer_class = FollowSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        return User.objects.filter(following__user=self.request.user)
