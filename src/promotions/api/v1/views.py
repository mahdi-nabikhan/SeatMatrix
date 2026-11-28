from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from operations.models import Showtime
from orders.api.v1.views import _resolve_owner
from orders.redis_locks import get_cart
from promotions.models import Coupon, DiscountRule
from promotions.services import apply_promotions
from .permissions import IsCinemaManager
from .serializers import (
    CouponSerializer,
    DiscountRuleSerializer,
    PromoPreviewInputSerializer,
)


class CartPromotionPreviewApiView(generics.GenericAPIView):
    """Preview the best applicable discount for the user's current Redis cart without consuming coupons."""
  
    permission_classes = [permissions.AllowAny]
    serializer_class = PromoPreviewInputSerializer

    def post(self, request):
        """Calculate total, discount, and final payable amount for the active cart."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        owner_id, _ = _resolve_owner(request, generate_if_missing=False)
        cart = get_cart(owner_id) if owner_id else None
        if not cart or not cart.get('seat_ids'):
            raise ValidationError({'detail': 'سبد خرید شما خالی است یا منقضی شده است.'})

        showtime = get_object_or_404(Showtime, id=cart['showtime_id'])
        total_amount = Decimal(showtime.base_price) * len(cart['seat_ids'])

        result = apply_promotions(
            total_amount=total_amount,
            showtime_start_time=showtime.start_time,
            coupon_code=serializer.validated_data.get('coupon_code'),
            consume=False,
        )

        return Response(
            {
                'total_amount': total_amount,
                'discount_amount': result['discount_amount'],
                'final_amount': result['final_amount'],
                'applied_type': result['applied_type'],
                'applied_name': result['applied_name'],
            },
            status=status.HTTP_200_OK,
        )


class CouponListCreateApiView(generics.ListCreateAPIView):
    """List existing coupons or create a new coupon for the active cinema tenant."""

    permission_classes = [IsCinemaManager]
    serializer_class = CouponSerializer
    queryset = Coupon.objects.all().order_by('-id')


class CouponDetailApiView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific Coupon in the active cinema tenant."""
    permission_classes = [IsCinemaManager]
    serializer_class = CouponSerializer
    queryset = Coupon.objects.all()


class DiscountRuleListCreateApiView(generics.ListCreateAPIView):
    """List existing discount rules or create a new weekday rule for the active tenant."""
    permission_classes = [IsCinemaManager]
    serializer_class = DiscountRuleSerializer
    queryset = DiscountRule.objects.all().order_by('-id')


class DiscountRuleDetailApiView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific DiscountRule in the active cinema tenant."""
    permission_classes = [IsCinemaManager]
    serializer_class = DiscountRuleSerializer
    queryset = DiscountRule.objects.all()