from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import BasePermission


class CustomPermission(BasePermission):
    """
    Allows access only to super admin users.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )
