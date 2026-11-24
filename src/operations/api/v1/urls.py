from django.urls import path
from .views import (
    # CinemaBranch
    CinemaBranchListApiView,
    CinemaBranchDetailApiView,
    CinemaBranchRegisterApiView,
    CinemaBranchManageApiView,
    CinemaBranchImageCreateApiView,
    CinemaBranchImageManageApiView,
    # Hall
    HallListApiView,
    HallDetailApiView,
    HallRegisterApiView,
    HallManageApiView,
    HallImageCreateApiView,
    HallImageManageApiView,
    # Seat
    SeatListApiView,
    SeatCreateApiView,
    SeatBulkCreateApiView,
    SeatManageApiView,
    # Showtime & ShowtimeSeat
    ShowtimeListApiView,
    ShowtimeDetailApiView,
    ShowtimeCreateApiView,
    ShowtimeManageApiView,
    ShowtimeSeatStatusUpdateApiView,
    ActiveMovieShowTimeListApiView
)

urlpatterns = [
    # ==================== CinemaBranch ====================
    path('branches/', CinemaBranchListApiView.as_view(), name='branch-list'),
    path('branches/register/', CinemaBranchRegisterApiView.as_view(), name='branch-register'),
    path('branches/<int:pk>/', CinemaBranchDetailApiView.as_view(), name='branch-detail'),
    path('branches/<int:pk>/manage/', CinemaBranchManageApiView.as_view(), name='branch-manage'),
    path('branches/images/create/', CinemaBranchImageCreateApiView.as_view(), name='branch-image-create'),
    path('branches/images/<int:pk>/manage/', CinemaBranchImageManageApiView.as_view(), name='branch-image-manage'),

    # ==================== Hall ====================
    path('halls/', HallListApiView.as_view(), name='hall-list'),
    path('branches/<int:pk>/halls/register/', HallRegisterApiView.as_view(), name='hall-register'),
    path('halls/<int:pk>/', HallDetailApiView.as_view(), name='hall-detail'),
    path('halls/<int:pk>/manage/', HallManageApiView.as_view(), name='hall-manage'),
    path('halls/images/create/', HallImageCreateApiView.as_view(), name='hall-image-create'),
    path('halls/images/<int:pk>/manage/', HallImageManageApiView.as_view(), name='hall-image-manage'),

    # ==================== Seat ====================
    path('halls/<int:hall_pk>/seats/', SeatListApiView.as_view(), name='seat-list'),
    path('seats/create/', SeatCreateApiView.as_view(), name='seat-create'),
    path('seats/bulk-create/', SeatBulkCreateApiView.as_view(), name='seat-bulk-create'),
    path('seats/<int:pk>/manage/', SeatManageApiView.as_view(), name='seat-manage'),

    # ==================== Showtime & ShowtimeSeat ====================
    path('showtimes/', ShowtimeListApiView.as_view(), name='showtime-list'),
    path('showtimes/create/', ShowtimeCreateApiView.as_view(), name='showtime-create'),
    path('showtimes/<int:pk>/', ShowtimeDetailApiView.as_view(), name='showtime-detail'),
    path('showtimes/<int:pk>/manage/', ShowtimeManageApiView.as_view(), name='showtime-manage'),
    path('showtime-seats/<int:pk>/status/', ShowtimeSeatStatusUpdateApiView.as_view(), name='showtime-seat-status'),
    path('movies/active-showtimes/', ActiveMovieShowTimeListApiView.as_view(), name='active-movie-showtimes'),
]