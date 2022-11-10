from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Пермишн предоставляет доступ к безопасным методам для
    анонимных пользователей и полный доступ для админов и авторизованных
    пользователей."""

    def has_permission(self, request, view):
        return (request.user.is_authenticated
                or request.method in permissions.SAFE_METHODS)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user and request.user.is_authenticated:
            return (request.user == obj.author
                    or request.user.is_superuser)
        return False
