from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_tenant_manager(user, tenant) -> bool:
    """Return True if the user is a superuser or the manager owning `tenant`."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not tenant or tenant.schema_name == 'public':
        return False

    manager_profile = getattr(user, 'manager_profile', None)
    return bool(
        manager_profile and getattr(tenant, 'manager_id', None) == manager_profile.id
    )


def is_tenant_staff(user, tenant) -> bool:
    """Return True if the user has an active Staff profile bound to `tenant`."""
    if not user or not user.is_authenticated:
        return False
    if not tenant or tenant.schema_name == 'public':
        return False

    staff_profile = getattr(user, 'staff_profile', None)
    return bool(
        staff_profile and staff_profile.is_active and staff_profile.cinema_id == tenant.id
    )


class IsCinemaManager(BasePermission):
    """Allow access only to the manager of the active cinema tenant (or superusers)."""

    def has_permission(self, request, view):
        """Verify the authenticated user manages `request.tenant`."""
        return is_tenant_manager(request.user, request.tenant)


class IsManagerOrBranchAdmin(BasePermission):
    """Allow read access to anyone and write access to the cinema manager or branch admin."""

    def has_permission(self, request, view):
        """Allow safe methods publicly; require tenant manager or staff for mutations."""
        if request.method in SAFE_METHODS:
            return True
        return is_tenant_manager(request.user, request.tenant) or is_tenant_staff(
            request.user, request.tenant
        )

    def has_object_permission(self, request, view, obj):
        """Authorize object mutations for the tenant manager or an admin of the target branch."""
        if request.method in SAFE_METHODS:
            return True
        if is_tenant_manager(request.user, request.tenant):
            return True

        if hasattr(obj, 'branch_admins'):
            branch = obj
        elif hasattr(obj, 'branch'):
            branch = obj.branch
        elif hasattr(obj, 'hall'):
            branch = obj.hall.branch
        elif hasattr(obj, 'showtime'):
            branch = obj.showtime.hall.branch
        else:
            return False

        if not is_tenant_staff(request.user, request.tenant):
            return False

        if branch.branch_admins.model.__name__ == 'Staff':
            return branch.branch_admins.filter(
                user_id=request.user.id,
                is_active=True,
            ).exists()
        return branch.branch_admins.filter(id=request.user.id).exists()