from django.urls import path
from . import views

app_name = 'cinemas'

urlpatterns = [

    path('register/', views.CinemaRegisterApiView.as_view(), name='cinema-register'),
    
  
    path('list/', views.CinemaListApiView.as_view(), name='cinema-list'),
    

    path('detail/<int:pk>/', views.CinemaDetailApiView.as_view(), name='cinema-detail'),
    

    path('update/<int:pk>/', views.CinemaUpdateApiview.as_view(), name='cinema-update'),
    

    path('delete/', views.CinemaDeleteApiView.as_view(), name='cinema-delete'),
    path('movies/', views.MovieListApiView.as_view(), name='movie-list'),
    path('movies/register/', views.MovieRegisterApiview.as_view(), name='movie-register'),
    path('movies/recommended/', views.RecommendedMovieListApiView.as_view(), name='movie-recommended'),
    path('movies/<int:pk>/', views.MovieDetailApiview.as_view(), name='movie-detail'),
    path('movies/<int:pk>/manage/', views.MovieUpdateAndDeleteApiView.as_view(), name='movie-update-delete'),
    
    
    
]