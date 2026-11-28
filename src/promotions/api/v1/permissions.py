from rest_framework import permissions


class IsCinemaManager(permissions.BasePermission):
    """Allow access only to the manager owning the active cinema tenant (or superusers)."""
    def has_permission(self, request, view):
        """Return True if the authenticated user is a superuser or owns `request.tenant`."""
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        tenant = getattr(request, 'tenant', None)
        manager = getattr(tenant, 'manager', None)
        return bool(manager and manager.user_id == user.id)