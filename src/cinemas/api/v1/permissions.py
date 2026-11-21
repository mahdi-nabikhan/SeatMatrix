from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsCinemaManagerOrStaffForMovie(BasePermission):
    """
    - GET/HEAD/OPTIONS: برای همه آزاد
    - POST: فقط منیجر یا استافِ فعالِ همان سینمای فعلی (request.tenant)
    - PUT/PATCH/DELETE: فقط منیجر یا استافِ فعالِ همان سینمایی که فیلم را ساخته
    """

    def _is_tenant_manager_or_staff(self, user, tenant):
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        manager_profile = getattr(user, 'manager_profile', None)
        if manager_profile and getattr(manager_profile, 'cinema', None) == tenant:
            return True

        staff_profile = getattr(user, 'staff_profile', None)
        if staff_profile and staff_profile.is_active and staff_profile.cinema_id == tenant.id:
            return True

        return False

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return self._is_tenant_manager_or_staff(request.user, request.tenant)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if request.user.is_superuser:
            return True

        movie = obj.movie if hasattr(obj, 'movie') else obj

  
        is_owner_cinema = (movie.created_by_cinema_id == request.tenant.id)
        return is_owner_cinema and self._is_tenant_manager_or_staff(request.user, request.tenant)