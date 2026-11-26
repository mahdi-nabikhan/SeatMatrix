from django.urls import path
from .views import (
    CartPromotionPreviewApiView,
    CouponDetailApiView,
    CouponListCreateApiView,
    DiscountRuleDetailApiView,
    DiscountRuleListCreateApiView,
)

urlpatterns = [
    path('preview/', CartPromotionPreviewApiView.as_view(), name='promotion-preview'),
    path('coupons/', CouponListCreateApiView.as_view(), name='coupon-list-create'),
    path('coupons/<int:pk>/', CouponDetailApiView.as_view(), name='coupon-detail'),
    path('rules/', DiscountRuleListCreateApiView.as_view(), name='discount-rule-list-create'),
    path('rules/<int:pk>/', DiscountRuleDetailApiView.as_view(), name='discount-rule-detail'),
]