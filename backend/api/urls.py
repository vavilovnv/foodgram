from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.views import (CustomUserViewSet, FollowListView,  # isort:skip
                         FollowViewSet)  # isort:skip

from .views import (IngredientsViewSet, RecipesViewSet,  # isort:skip
                    TagsViewSet)  # isort:skip

router = DefaultRouter()
router.register('users', CustomUserViewSet, basename='users')
router.register('tags', TagsViewSet, basename='tags')
router.register('ingredients', IngredientsViewSet, basename='ingredients')
router.register('recipes', RecipesViewSet, basename='recipes')

urlpatterns = [
    path(
        'users/subscriptions/',
        FollowListView.as_view(),
        name='subscriptions'
    ),
    path(
        'users/<int:user_id>/subscribe/',
        FollowViewSet.as_view(),
        name='subscribe'
    ),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
