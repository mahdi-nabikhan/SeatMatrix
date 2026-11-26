from django.urls import path
from .views import (
    CartHoldApiView,
    CheckoutApiView,
    ClaimGuestCartApiView,
    CustomerOrderDetailApiView,
    CustomerOrderListApiView,
    ShowtimeLiveSeatMapApiView,
)

urlpatterns = [
    path('showtimes/<int:showtime_id>/seats/', ShowtimeLiveSeatMapApiView.as_view(), name='showtime-live-seats'),
    path('cart/', CartHoldApiView.as_view(), name='order-cart'),
    path('cart/claim/', ClaimGuestCartApiView.as_view(), name='order-cart-claim'),
    path('checkout/', CheckoutApiView.as_view(), name='order-checkout'),
    path('', CustomerOrderListApiView.as_view(), name='order-list'),
    path('<str:order_number>/', CustomerOrderDetailApiView.as_view(), name='order-detail'),
]