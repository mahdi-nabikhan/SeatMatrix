from rest_framework import permissions


class IsCinemaManager(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        tenant = getattr(request, 'tenant', None)
        manager = getattr(tenant, 'manager', None)
        return bool(manager and manager.user_id == user.id)