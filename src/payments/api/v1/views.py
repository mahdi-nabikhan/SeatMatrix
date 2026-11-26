from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from orders.models import Order
from payments.services import initiate_payment, verify_payment
from .serializers import PaymentRequestInputSerializer, TransactionSerializer


class PaymentRequestApiView(generics.GenericAPIView):
    """شروع پرداخت برای یک سفارش PENDING و دریافت لینک درگاه ZarinPal"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentRequestInputSerializer

    def post(self, request):
        customer = getattr(request.user, 'customer_profile', None)
        if not customer:
            return Response(
                {'detail': 'پروفایل مشتری یافت نشد.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(
            Order,
            order_number=serializer.validated_data['order_number'],
            customer=customer,
        )

        # ساخت خودکار آدرس کال‌بک روی همان دامنه‌ی تننت فعلی (مثلاً http://cinema1.lvh.me:8000/api/v1/payments/verify/)
        callback_url = request.build_absolute_uri(reverse('payment-verify'))
        result = initiate_payment(order=order, callback_url=callback_url)

        return Response(
            {
                'transaction_id': str(result['transaction'].transaction_id),
                'authority': result['authority'],
                'payment_url': result['payment_url'],
            },
            status=status.HTTP_200_OK,
        )


class PaymentVerifyApiView(generics.GenericAPIView):
    """اندپوینت کال‌بک درگاه زرین‌پال (?Authority=...&Status=OK|NOK)"""
    permission_classes = [permissions.AllowAny]
    serializer_class = TransactionSerializer

    def get(self, request):
        authority = request.query_params.get('Authority')
        gateway_status = request.query_params.get('Status', '')

        if not authority:
            return Response(
                {'detail': 'پارامتر Authority ارسال نشده است.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tx = verify_payment(authority=authority, gateway_status=gateway_status)
        http_status = status.HTTP_200_OK if tx.status == 'SUCCESS' else status.HTTP_400_BAD_REQUEST
        return Response(TransactionSerializer(tx).data, status=http_status)