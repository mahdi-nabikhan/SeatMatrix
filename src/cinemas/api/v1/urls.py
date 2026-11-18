from django.urls import path
from . import views

app_name = 'cinemas'

urlpatterns = [

    path('register/', views.CinemaRegisterApiView.as_view(), name='cinema-register'),
    
  
    path('list/', views.CinemaListApiView.as_view(), name='cinema-list'),
    

    path('detail/<int:pk>/', views.CinemaDetailApiView.as_view(), name='cinema-detail'),
    

    path('update/<int:pk>/', views.CinemaUpdateApiview.as_view(), name='cinema-update'),
    

    path('delete/', views.CinemaDeleteApiView.as_view(), name='cinema-delete'),
]