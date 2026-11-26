from django.urls import path
from .views import StaffListApiView, StaffDetailApiView, StaffMeApiView

urlpatterns = [
    path('staff/', StaffListApiView.as_view(), name='staff-list'),
    path('staff/me/', StaffMeApiView.as_view(), name='staff-me'),
    path('staff/<int:pk>/', StaffDetailApiView.as_view(), name='staff-detail'),
]