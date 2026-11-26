from rest_framework import serializers
from promotions.models import Coupon, DiscountRule


class PromoPreviewInputSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id',
            'code',
            'discount_percentage',
            'max_discount_amount',
            'capacity',
            'used_count',
            'valid_from',
            'valid_to',
            'is_active',
        ]
        read_only_fields = ['id', 'used_count']

    def validate_code(self, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError('کد تخفیف نمی‌تواند خالی باشد.')

        qs = Coupon.objects.filter(code__iexact=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError('این کد تخفیف قبلاً ثبت شده است.')

        return cleaned

    def validate_max_discount_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('سقف مبلغ تخفیف باید بیشتر از صفر باشد.')
        return value

    def validate(self, attrs):
        valid_from = attrs.get('valid_from', getattr(self.instance, 'valid_from', None))
        valid_to = attrs.get('valid_to', getattr(self.instance, 'valid_to', None))

        if valid_from and valid_to and valid_to <= valid_from:
            raise serializers.ValidationError({
                'valid_to': 'تاریخ پایان اعتبار باید بعد از تاریخ شروع باشد.'
            })

        return attrs


class DiscountRuleSerializer(serializers.ModelSerializer):
    WEEKDAY_NAMES = {
        0: 'دوشنبه',
        1: 'سه‌شنبه',
        2: 'چهارشنبه',
        3: 'پنج‌شنبه',
        4: 'جمعه',
        5: 'شنبه',
        6: 'یکشنبه',
    }
    day_of_week_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DiscountRule
        fields = [
            'id',
            'name',
            'discount_percentage',
            'day_of_week',
            'day_of_week_display',
            'is_active',
        ]
        read_only_fields = ['id', 'day_of_week_display']

    def get_day_of_week_display(self, obj) -> str | None:
        if obj.day_of_week is None:
            return None
        return self.WEEKDAY_NAMES.get(obj.day_of_week)

    def validate_day_of_week(self, value):
        if value is not None and not (0 <= value <= 6):
            raise serializers.ValidationError('روز هفته باید عددی بین ۰ (دوشنبه) تا ۶ (یکشنبه) باشد.')
        return value