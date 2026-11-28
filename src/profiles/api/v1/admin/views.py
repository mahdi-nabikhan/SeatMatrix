from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions

from cinemas.api.v1.permissions import IsCinemaManager 
from profiles.models import Staff
from .serializers import StaffSerializer


class StaffListApiView(generics.ListAPIView):
    """List all staff members belonging to the active cinema tenant.

    Restricted to managers of the current cinema (`IsCinemaManager`).
    """
    permission_classes =[IsCinemaManager]
    serializer_class = StaffSerializer
    def get_queryset(self):
        """Return staff records scoped to `request.tenant` with prefetched users."""
        return Staff.objects.filter(cinema = self.request.tenant).select_related('user')
    
    
    
    
class StaffDetailApiView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or remove a staff member in the active cinema tenant.

    Restricted to managers of the current cinema (`IsCinemaManager`).
    """
    permission_classes = [IsCinemaManager]
    serializer_class = StaffSerializer
    
    
    def get_queryset(self):
        """Return staff records scoped to `request.tenant` with prefetched users."""
        return Staff.objects.filter(cinema=self.request.tenant).select_related('user')
    
    
    
    
class StaffMeApiView(generics.RetrieveAPIView):
    """Retrieve the authenticated active staff member's own profile."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StaffSerializer
    
    
    
    def get_object(self):
        """Return the active Staff profile for the current user or raise 404."""
        return get_object_or_404(
            Staff.objects.select_related('user','cinema'),
            user=self.request.user,
            is_active=True
        )
    