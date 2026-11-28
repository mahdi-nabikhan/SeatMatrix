import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django_tenants.utils import schema_context

from promotions.models import Coupon, DiscountRule


@pytest.mark.django_db(transaction=True)
def test_coupon_and_discount_rule_models(setup_promo_tenant):
    env = setup_promo_tenant('test_promo_mdl', 'Promo Model Cinema', 'promo-mdl.lvh.me')
    tenant = env['tenant']

    with schema_context(tenant.schema_name):

        coupon = Coupon.objects.create(code='YALDA', discount_percentage=25)
        assert coupon.capacity == 100
        assert coupon.used_count == 0
        assert coupon.is_active is True

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Coupon.objects.create(code='YALDA', discount_percentage=10)

        for bad_pct in (0, 101):
            bad_coupon = Coupon(code=f'BAD{bad_pct}', discount_percentage=bad_pct)
            with pytest.raises(ValidationError):
                bad_coupon.full_clean()

 
        rule = DiscountRule.objects.create(name='سه‌شنبه نیم‌بها', discount_percentage=50, day_of_week=1)
        assert rule.is_active is True
        assert str(rule) == 'سه‌شنبه نیم‌بها'

    
        for bad_pct in (0, 101):
            bad_rule = DiscountRule(name='Bad Rule', discount_percentage=bad_pct)
            with pytest.raises(ValidationError):
                bad_rule.full_clean()