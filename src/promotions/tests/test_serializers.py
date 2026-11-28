from datetime import timedelta

import pytest
from django.utils import timezone
from django_tenants.utils import schema_context

from promotions.api.v1.serializers import (
    CouponSerializer,
    DiscountRuleSerializer,
    PromoPreviewInputSerializer,
)
from promotions.models import Coupon, DiscountRule


@pytest.mark.django_db(transaction=True)
def test_promotion_serializers_validation(setup_promo_tenant):
    env = setup_promo_tenant('test_promo_ser', 'Promo Ser Cinema', 'promo-ser.lvh.me')
    tenant = env['tenant']
    now = timezone.now()

    assert PromoPreviewInputSerializer(data={}).is_valid()
    assert PromoPreviewInputSerializer(data={'coupon_code': ''}).is_valid()
    assert PromoPreviewInputSerializer(data={'coupon_code': None}).is_valid()
    assert not PromoPreviewInputSerializer(data={'coupon_code': 'A' * 51}).is_valid()

    with schema_context(tenant.schema_name):

        ser = CouponSerializer(
            data={
                'code': '  spring15  ',
                'discount_percentage': 15,
                'used_count': 99,
            }
        )
        assert ser.is_valid(), ser.errors
        coupon = ser.save()
        assert coupon.code == 'SPRING15'
        assert coupon.used_count == 0


        assert not CouponSerializer(data={'code': '   ', 'discount_percentage': 10}).is_valid()

   
        dup_ser = CouponSerializer(data={'code': 'spring15', 'discount_percentage': 20})
        assert not dup_ser.is_valid()
        assert 'code' in dup_ser.errors

        upd_ser = CouponSerializer(
            instance=coupon,
            data={'code': 'spring15', 'discount_percentage': 25},
            partial=True,
        )
        assert upd_ser.is_valid(), upd_ser.errors

        cap_ser = CouponSerializer(
            data={'code': 'ZERO', 'discount_percentage': 10, 'max_discount_amount': 0}
        )
        assert not cap_ser.is_valid()
        assert 'max_discount_amount' in cap_ser.errors

        date_ser = CouponSerializer(
            data={
                'code': 'BADDATE',
                'discount_percentage': 10,
                'valid_from': now + timedelta(days=2),
                'valid_to': now + timedelta(days=1),
            }
        )
        assert not date_ser.is_valid()
        assert 'valid_to' in date_ser.errors

  
        rule_tue = DiscountRule.objects.create(name='سه‌شنبه', discount_percentage=50, day_of_week=1)
        rule_any = DiscountRule.objects.create(name='عمومی', discount_percentage=10, day_of_week=None)
        assert DiscountRuleSerializer(rule_tue).data['day_of_week_display'] == 'سه‌شنبه'
        assert DiscountRuleSerializer(rule_any).data['day_of_week_display'] is None

        bad_day_ser = DiscountRuleSerializer(
            data={'name': 'Bad', 'discount_percentage': 10, 'day_of_week': 7}
        )
        assert not bad_day_ser.is_valid()
        assert 'day_of_week' in bad_day_ser.errors