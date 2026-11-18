from django.urls import path
from . import views

app_name = 'customer'

urlpatterns = [
   
    path('register/', views.CustomerRegisterationApiView.as_view(), name='customer-register'),
    path('profile/', views.CustomerDetailAPIview.as_view(), name='customer-profile'),
    path('profile/edit/', views.CustomerUpdateApiView.as_view(), name='customer-profile-edit'),
]