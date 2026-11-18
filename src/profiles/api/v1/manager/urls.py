from django.urls import path
from . import views

app_name = 'manager'

urlpatterns = [
    path('register/', views.ManagerRegisterApiView.as_view(), name='manager-register'),
    path('profile/', views.ManagerDetailApiView.as_view(), name='manager-profile'),
]