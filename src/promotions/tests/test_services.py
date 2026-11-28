from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from promotions.models import Coupon, DiscountRule
from promotions.services import apply_promotions, validate_coupon


@pytest.mark.django_db(transaction=True)
def test_coupon_validation_and_apply_promotions_logic(setup_promo_tenant):
    env = setup_promo_tenant('test_promo_svc', 'Promo Svc Cinema', 'promo-svc.lvh.me')
    tenant = env['tenant']
    now = timezone.now()
    showtime_dt = now + timedelta(days=1)
    weekday = timezone.localtime(showtime_dt).weekday()

    with schema_context(tenant.schema_name):
        # کوپن‌های نامعتبر: غیرفعال، منقضی، آینده، تکمیل ظرفیت
        Coupon.objects.create(code='INACTIVE', discount_percentage=20, is_active=False)
        Coupon.objects.create(code='EXPIRED', discount_percentage=20, valid_to=now - timedelta(hours=1))
        Coupon.objects.create(code='FUTURE', discount_percentage=20, valid_from=now + timedelta(days=2))
        Coupon.objects.create(code='FULL', discount_percentage=20, capacity=2, used_count=2)

        for bad_code in ('NOTEXIST', 'INACTIVE', 'EXPIRED', 'FUTURE', 'FULL'):
            with pytest.raises(ValidationError):
                validate_coupon(bad_code)

        # کوپن معتبر با سقف تخفیف (۳۰٪ از ۲۰۰,۰۰۰ = ۶۰,۰۰۰ ولی سقف ۴۰,۰۰۰)
        coupon = Coupon.objects.create(
            code='YALDA30',
            discount_percentage=30,
            max_discount_amount=Decimal('40000'),
            capacity=5,
        )
        # قانون هفتگی ۲۵٪ از ۲۰۰,۰۰۰ = ۵۰,۰۰۰ (بیشتر از سقف کوپن!)
        DiscountRule.objects.create(
            name='نیم‌بهای ویژه',
            discount_percentage=25,
            day_of_week=weekday,
            is_active=True,
        )

        # وقتی قانون هفتگی (۵۰,۰۰۰) از کوپن (۴۰,۰۰۰) بیشتر است، قانون هفتگی انتخاب و کوپن مصرف نمی‌شود
        with transaction.atomic():
            res_rule = apply_promotions(
                total_amount=Decimal('200000'),
                showtime_start_time=showtime_dt,
                coupon_code='yalda30',
                consume=True,
            )
        assert res_rule['applied_type'] == 'DISCOUNT_RULE'
        assert res_rule['discount_amount'] == Decimal('50000')
        assert res_rule['final_amount'] == Decimal('150000')
        coupon.refresh_from_db()
        assert coupon.used_count == 0

        # روی مبلغ ۱۰۰,۰۰۰: کوپن ۳۰٪ = ۳۰,۰۰۰ > قانون ۲۵٪ = ۲۵,۰۰۰ -> کوپن انتخاب و مصرف می‌شود
        with transaction.atomic():
            res_coupon = apply_promotions(
                total_amount=Decimal('100000'),
                showtime_start_time=showtime_dt,
                coupon_code='  yalda30  ',
                consume=True,
            )
        assert res_coupon['applied_type'] == 'COUPON'
        assert res_coupon['applied_name'] == 'YALDA30'
        assert res_coupon['discount_amount'] == Decimal('30000')
        assert res_coupon['final_amount'] == Decimal('70000')
        coupon.refresh_from_db()
        assert coupon.used_count == 1