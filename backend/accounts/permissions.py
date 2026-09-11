from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

User = get_user_model()


class IsAdminUserRole(BasePermission):
    message = "Admin role is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == User.Role.ADMIN
        )


class IsEmployeeOwner(BasePermission):
    message = "You can only access your own reviews."

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            user and user.is_authenticated and obj.employee_id == user.id
        )
