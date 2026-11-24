from rest_framework.permissions import BasePermission, SAFE_METHODS


def is_tenant_manager(user, tenant):
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


def is_tenant_staff(user, tenant):
    if not user or not user.is_authenticated:
        return False
    if not tenant or tenant.schema_name == 'public':
        return False

    staff_profile = getattr(user, 'staff_profile', None)
    return bool(
        staff_profile and staff_profile.is_active and staff_profile.cinema_id == tenant.id
    )


class IsCinemaManager(BasePermission):
    """فقط منیجر همین سینما (مثلاً برای ساخت و حذف شعبه جدید)"""
    def has_permission(self, request, view):
        return is_tenant_manager(request.user, request.tenant)


class IsManagerOrBranchAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_tenant_manager(request.user, request.tenant) or is_tenant_staff(request.user, request.tenant)

    def has_object_permission(self, request, view, obj):
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
        else:
            return False

        if not is_tenant_staff(request.user, request.tenant):
            return False


        if branch.branch_admins.model.__name__ == 'Staff':
            return branch.branch_admins.filter(user_id=request.user.id, is_active=True).exists()
        return branch.branch_admins.filter(id=request.user.id).exists()