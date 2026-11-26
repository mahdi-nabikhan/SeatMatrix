from django.db import models
import uuid

class Order(models.Model):
    """
    سفارش اصلی که می‌تواند شامل یک یا چند بلیت (صندلی) باشد.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending Payment'),
        ('PAID', 'Paid Successfully'),
        ('CANCELLED', 'Cancelled (Timeout)'),
        ('REFUNDED', 'Refunded'),
    )
    
    
    customer = models.ForeignKey('profiles.Customer', on_delete=models.PROTECT, related_name='orders')
    
   
    order_number = models.CharField(max_length=20, unique=True, db_index=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.order_number} | Customer: {self.customer.user.username} | {self.status}"


class Ticket(models.Model):
    """
    هر رکورد از این جدول معادل یک صندلی خریداری شده در یک سفارش است.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tickets')
    
  
    showtime_seat = models.OneToOneField('operations.ShowtimeSeat', on_delete=models.PROTECT, related_name='ticket')
    
    price = models.DecimalField(max_digits=10, decimal_places=0)
    ticket_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.ticket_code} | Order: {self.order.order_number}"