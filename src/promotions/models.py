from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Coupon(models.Model):
    """Tenant-scoped promotional coupon with optional cap, usage limit, and validity window."""
    code = models.CharField(max_length=50, unique=True, help_text="کد تخفیف (مثلا: YALDA)")
    discount_percentage = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="درصد تخفیف (۱ تا ۱۰۰)"
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=0, null=True, blank=True,
        help_text="سقف مبلغ تخفیف (اختیاری)"
    )
    capacity = models.PositiveIntegerField(default=100, help_text="تعداد دفعات مجاز استفاده")
    used_count = models.PositiveIntegerField(default=0, help_text="تعداد دفعات استفاده شده")
    
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Coupon: {self.code} ({self.discount_percentage}%)"


class DiscountRule(models.Model):
    """Automatic tenant-scoped percentage discount rule optionally tied to a weekday."""
    name = models.CharField(max_length=100, help_text="عنوان (مثلا: سه‌شنبه‌های نیم‌بها)")
    discount_percentage = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    # 0=Monday, 1=Tuesday, 2=Wednesday, ...
    day_of_week = models.PositiveSmallIntegerField(
        null=True, blank=True, 
        help_text="اعمال خودکار در روز خاصی از هفته (۰=دوشنبه تا ۶=یکشنبه)"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name