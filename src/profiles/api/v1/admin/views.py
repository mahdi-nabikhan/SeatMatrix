from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions

from cinemas.api.v1.permissions import IsCinemaManager  # مسیر جدیدی که پرمیشن رو گذاشتی
from profiles.models import Staff
from .serializers import StaffSerializer


class StaffListApiView(generics.ListAPIView):
    
    
    permission_classes =[IsCinemaManager]
    serializer_class = StaffSerializer
    def get_queryset(self):
        return Staff.objects.filter(cinema = self.request.tenant).select_related('user')
    
    
    
    
class StaffDetailApiView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsCinemaManager]
    serializer_class = StaffSerializer
    
    
    def get_queryset(self):
        return Staff.objects.filter(cinema=self.request.tenant).select_related('user')
    
    
    
    
class StaffMeApiView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StaffSerializer
    
    
    
    def get_object(self):
        return get_object_or_404(
            Staff.objects.select_related('user','cinema'),
            user=self.request.user,
            is_active=True
        )
    