from django.db import models
from django.conf import settings
from cinemas.models import Cinema

class Manager(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='manager_profile')
    
 
    cinema = models.OneToOneField(Cinema, on_delete=models.CASCADE, related_name='manager')
    
    bank_iban = models.CharField(max_length=24, null=True, blank=True)

    def __str__(self):
        return f"Manager: {self.user.username} - {self.cinema.name}"

class Staff(models.Model):
    SHIFT_CHOICES = (
        ('MORNING', 'Morning Shift'),
        ('EVENING', 'Evening Shift'),
        ('FULL', 'Full Time'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    

    cinema = models.ForeignKey(Cinema, on_delete=models.CASCADE, related_name='staff')
    
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default='MORNING')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Staff: {self.user.username} - {self.cinema.name}"

class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile')
    loyalty_points = models.PositiveIntegerField(default=0)
    firstname = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    age = models.CharField(max_length=255,null=True,blank=True)
    
    def __str__(self):
        return f"Customer: {self.user.username}"