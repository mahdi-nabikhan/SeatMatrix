import uuid
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from operations.models import Showtime, ShowtimeSeat
from orders.models import Order
from orders.redis_locks import (
    build_owner_id,
    claim_guest_cart,
    get_cart,
    get_locked_seats_map,
    release_cart,
)
from orders.services import checkout_cart_to_order, hold_showtime_seats
from .serializers import (
    HoldSeatsInputSerializer,
    LiveSeatSerializer,
    OrderSerializer,
)


def _resolve_owner(request, generate_if_missing: bool = False) -> tuple[str | None, str | None]:
    """برمی‌گرداند: (owner_id, guest_token)"""
    if request.user and request.user.is_authenticated:
        return f"user:{request.user.id}", None

    guest_token = request.headers.get('X-Guest-Token')
    if not guest_token and generate_if_missing:
        guest_token = str(uuid.uuid4())

    return build_owner_id(request.user, guest_token), guest_token


class ShowtimeLiveSeatMapApiView(APIView):
    """نقشه زنده صندلی‌های سانس (وضعیت SOLD از Postgres + قفل‌های فعال از Redis)"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, showtime_id):
        showtime = get_object_or_404(Showtime, id=showtime_id)
        owner_id, _ = _resolve_owner(request, generate_if_missing=False)

        showtime_seats = list(
            ShowtimeSeat.objects.filter(showtime=showtime)
            .select_related('seat')
            .order_by('seat__row_label', 'seat__seat_number')
        )

        seat_ids = [ss.id for ss in showtime_seats]
        locked_map = get_locked_seats_map(showtime_id=showtime.id, seat_ids=seat_ids)

        seats_data = []
        for ss in showtime_seats:
            if ss.status == 'SOLD':
                live_status = 'SOLD'
            elif ss.id in locked_map:
                live_status = 'RESERVED_BY_ME' if (owner_id and locked_map[ss.id] == owner_id) else 'RESERVED'
            else:
                live_status = 'AVAILABLE'

            seats_data.append({
                'showtime_seat_id': ss.id,
                'row_label': ss.seat.row_label,
                'seat_number': ss.seat.seat_number,
                'is_vip': ss.seat.is_vip,
                'status': live_status,
            })

        return Response({
            'showtime_id': showtime.id,
            'base_price': showtime.base_price,
            'seats': LiveSeatSerializer(seats_data, many=True).data,
        })


class CartHoldApiView(generics.GenericAPIView):
    """
    - GET: مشاهده سبد خرید فعلی در Redis
    - POST: قفل اتمیک صندلی‌ها در Redis (مهمان یا لاگین‌شده)
    - DELETE: آزادسازی صندلی‌ها و خالی کردن سبد
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = HoldSeatsInputSerializer

    def get(self, request):
        owner_id, _ = _resolve_owner(request, generate_if_missing=False)
        if not owner_id:
            return Response({'cart': None})
        return Response({'cart': get_cart(owner_id)})

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        owner_id, guest_token = _resolve_owner(request, generate_if_missing=True)
        result = hold_showtime_seats(
            owner_id=owner_id,
            showtime_id=serializer.validated_data['showtime_id'],
            showtime_seat_ids=serializer.validated_data['showtime_seat_ids'],
        )

        if guest_token:
            result['guest_token'] = guest_token

        response = Response(result, status=status.HTTP_200_OK)
        if guest_token:
            response['X-Guest-Token'] = guest_token
        return response

    def delete(self, request):
        owner_id, _ = _resolve_owner(request, generate_if_missing=False)
        if owner_id:
            release_cart(owner_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClaimGuestCartApiView(APIView):
    """انتقال سبد و قفل‌های کاربر مهمان به اکانت پس از لاگین"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        guest_token = request.headers.get('X-Guest-Token')
        if not guest_token:
            return Response(
                {'detail': 'هدر X-Guest-Token ارسال نشده است.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = claim_guest_cart(guest_token=guest_token, user_id=request.user.id)
        if not cart:
            return Response(
                {'detail': 'سبد خرید معتبری برای این توکن مهمان یافت نشد یا منقضی شده است.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({'detail': 'سبد خرید با موفقیت منتقل شد.', 'cart': cart})


class CheckoutApiView(APIView):
    """تبدیل سبد Redis به Order و Ticket قطعی در Postgres"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        customer = getattr(request.user, 'customer_profile', None)
        if not customer:
            return Response(
                {'detail': 'فقط کاربران دارای پروفایل مشتری مجاز به ثبت سفارش هستند.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = checkout_cart_to_order(customer=customer)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class CustomerOrderListApiView(generics.ListAPIView):
    """لیست سفارش‌های مشتری"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        customer = getattr(self.request.user, 'customer_profile', None)
        if not customer:
            return Order.objects.none()
        return (
            Order.objects.filter(customer=customer)
            .prefetch_related('tickets__showtime_seat__seat')
            .order_by('-created_at')
        )


class CustomerOrderDetailApiView(generics.RetrieveAPIView):
    """جزئیات یک سفارش بر اساس order_number"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    lookup_field = 'order_number'

    def get_queryset(self):
        customer = getattr(self.request.user, 'customer_profile', None)
        if not customer:
            return Order.objects.none()
        return (
            Order.objects.filter(customer=customer)
            .prefetch_related('tickets__showtime_seat__seat')
        )