from django.urls import path
from .views import MarkNotificationReadApiView, MyNotificationListApiView

urlpatterns = [
    path('', MyNotificationListApiView.as_view(), name='notification-list'),
    path('<int:pk>/read/', MarkNotificationReadApiView.as_view(), name='notification-read'),
]