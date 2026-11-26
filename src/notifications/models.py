from django.db import models
from django.conf import settings

class SMSLog(models.Model):
    """
    لاگ و تاریخچه تمام پیامک‌های ارسال شده به کاربران (OTP, بلیت و ...)
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SENT', 'Sent Successfully'),
        ('FAILED', 'Failed to Send'),
    )
    phone_number = models.CharField(max_length=15)
    message = models.TextField()
    

    provider = models.CharField(max_length=50, default='Kavenegar')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
   
    provider_response = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SMS to {self.phone_number} | {self.status}"


class InAppNotification(models.Model):
    """
    نوتیفیکیشن‌های داخل سایت/اپلیکیشن برای اطلاع‌رسانی به کاربران و مدیران
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notif for {self.user.username}: {self.title}"