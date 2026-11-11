from django.db import models
import uuid

class Transaction(models.Model):
    """
    لاگ دقیق تمامی تراکنش‌های مالی و ارتباط با درگاه پرداخت.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending Gateway'),      # کاربر به درگاه منتقل شده
        ('SUCCESS', 'Payment Successful'),   # پرداخت موفق و تایید شده
        ('FAILED', 'Payment Failed'),        # پرداخت ناموفق (موجودی ناکافی، انصراف)
        ('REFUNDED', 'Refunded to User'),    # عودت وجه
    )

    # شناسه یکتا برای ارسال به درگاه (امن‌تر از آیدی عددی)
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # ارتباط یک به چند با سفارش (چون یک سفارش ممکنه چندبار تلاش برای پرداخت داشته باشه)
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='transactions')
    
    amount = models.DecimalField(max_digits=12, decimal_places=0, help_text="مبلغ ارسال شده به درگاه")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # اطلاعات اختصاصی درگاه (مثل زرین‌پال)
    gateway_name = models.CharField(max_length=50, default='ZarinPal')
    authority = models.CharField(max_length=255, null=True, blank=True, help_text="توکن ارجاع اولیه درگاه")
    ref_id = models.CharField(max_length=255, null=True, blank=True, help_text="کد پیگیری تراکنش موفق")
    card_pan = models.CharField(max_length=20, null=True, blank=True, help_text="شماره کارت ماسک شده")
    
    # لاگ خطاها برای پیگیری‌های پشتیبانی
    response_code = models.CharField(max_length=50, null=True, blank=True)
    response_message = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tx {self.transaction_id} | Order: {self.order.order_number} | {self.status}"