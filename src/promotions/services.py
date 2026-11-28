from decimal import Decimal
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from promotions.models import Coupon, DiscountRule




def _calc_percentage_discount(total_amount: Decimal,percentage: int,max_amount: Decimal | None = None) ->Decimal:
    """Compute an integer-floored percentage discount capped by `max_amount` and `total_amount`."""
    discount = (Decimal(total_amount) * Decimal(percentage)) // Decimal(100)
    if max_amount is not None:
        discount =  min(discount,Decimal(max_amount))
    return min(discount,Decimal(total_amount))



def validate_coupon (code:str,*,lock:bool = False) -> Coupon:
    """Validate a coupon code's active state, validity dates, and remaining capacity.

    Args:
        code: Case-insensitive coupon code string.
        lock: When True, acquires a row-level `SELECT FOR UPDATE` lock for atomic consumption.

    Returns:
        The validated `Coupon` instance.

    Raises:
        ValidationError: If the coupon does not exist, is inactive, outside its
            validity window, or has reached its usage capacity.
    """
    cleaned_code = code.strip()
    qs = Coupon.objects.select_for_update() if lock else Coupon.objects.all()
    
    
    coupon = qs.filter(code__iexact=cleaned_code).first()
    if not coupon or not coupon.is_active:
        raise ValidationError({'coupon_code': 'کد تخفیف معتبر یا فعال نیست.'})
    
    
    now = timezone.now()
    if coupon.valid_from and now  <  coupon.valid_from:
        raise ValidationError({'coupon_code': 'زمان استفاده از این کد تخفیف هنوز شروع نشده است.'})
    
    if coupon.valid_to and now > coupon.valid_to:
        raise ValidationError({'coupon_code': 'مهلت استفاده از این کد تخفیف به پایان رسیده است.'})
    
    if coupon.used_count >= coupon.capacity:
        raise ValidationError({'coupon_code': 'ظرفیت استفاده از این کد تخفیف تکمیل شده است.'})
    
    return coupon
 
 
def get_active_discount_rule(showtime_start_time) -> DiscountRule | None:
    """Return the highest-percentage active DiscountRule matching the showtime's local weekday."""

    local_weekday = timezone.localtime(showtime_start_time).weekday()
    return (
        DiscountRule.objects.filter(is_active=True, day_of_week=local_weekday)
        .order_by('-discount_percentage')
        .first()
    )




def apply_promotions(*,total_amount: Decimal,showtime_start_time,coupon_code: str | None = None,consume: bool = False) -> dict:
    """Evaluate applicable weekday rules and optional coupon, applying whichever saves more.

    Args:
        total_amount: Gross order amount before discounts.
        showtime_start_time: Aware datetime of the showtime used for weekday rule matching.
        coupon_code: Optional user-supplied coupon code.
        consume: If True and the coupon is selected, atomically increments `used_count`.

    Returns:
        A dict containing `discount_amount`, `final_amount`, `applied_type`,
        `applied_name`, and the applied `coupon` instance (or None).
    """
    total_amount = Decimal(total_amount)

    rule = get_active_discount_rule(showtime_start_time)
    rule_discount = (
        _calc_percentage_discount(total_amount, rule.discount_percentage)
        if rule
        else Decimal(0)
    )


    coupon = None
    coupon_discount = Decimal(0)
    if coupon_code and coupon_code.strip():
        coupon = validate_coupon(coupon_code, lock=consume)
        coupon_discount = _calc_percentage_discount(
            total_amount,
            coupon.discount_percentage,
            coupon.max_discount_amount,
        )


    if coupon and coupon_discount >= rule_discount and coupon_discount > 0:
        if consume:
            Coupon.objects.filter(pk=coupon.pk).update(used_count=F('used_count') + 1)

        return {
            'discount_amount': coupon_discount,
            'final_amount': total_amount - coupon_discount,
            'applied_type': 'COUPON',
            'applied_name': coupon.code,
            'coupon': coupon,
        }

    if rule and rule_discount > 0:
        return {
            'discount_amount': rule_discount,
            'final_amount': total_amount - rule_discount,
            'applied_type': 'DISCOUNT_RULE',
            'applied_name': rule.name,
            'coupon': None,
        }

    return {
        'discount_amount': Decimal(0),
        'final_amount': total_amount,
        'applied_type': None,
        'applied_name': None,
        'coupon': None,
    }