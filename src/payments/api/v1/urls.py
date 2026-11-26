from django.urls import path
from .views import PaymentRequestApiView, PaymentVerifyApiView

urlpatterns = [
    path('request/', PaymentRequestApiView.as_view(), name='payment-request'),
    path('verify/', PaymentVerifyApiView.as_view(), name='payment-verify'),
]