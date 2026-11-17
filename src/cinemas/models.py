from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.core.exceptions import ValidationError

# ==========================================
# بخش اول: داده‌های عمومی (Public Schema)
# ==========================================

class Address(models.Model):
    province = models.CharField(max_length=50, verbose_name="Province/State")
    city = models.CharField(max_length=50, verbose_name="City")
    full_address = models.TextField(verbose_name="Full Address")
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.province}, {self.city} - {self.full_address[:30]}"


class Cinema(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    manager = models.OneToOneField('profiles.Manager', on_delete=models.PROTECT, related_name='owned_cinema', null=True, blank=True)
    
    def __str__(self):
        return self.name


class CinemaBranch(TenantMixin):
    cinema = models.ForeignKey(Cinema, on_delete=models.CASCADE, related_name='branches', null=True, blank=True)
    address = models.OneToOneField(Address, on_delete=models.PROTECT, related_name='cinema_branch', null=True, blank=True)
    
    branch_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    facilities = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    auto_create_schema = True

    def clean(self):
        super().clean()
        
        # برای مستأجرهای واقعی (غیر از public)، سینما و آدرس اجباری است
        if self.schema_name != 'public':
            if not self.cinema:
                raise ValidationError({'cinema': 'تعیین سینما برای شعبه الزامی است.'})
            if not self.address:
                raise ValidationError({'address': 'ثبت آدرس برای شعبه الزامی است.'})

    def __str__(self):
        if self.schema_name == 'public':
            return "Public Core System"
        return f"{self.cinema.name} - {self.branch_name}"


class BranchDomain(DomainMixin):
    """آدرس دامنه اختصاصی مستأجر (مثلاً azadi.seatmatrix.ir)"""
    pass


class Movie(models.Model):
    """فیلم‌ها عمومی هستند و بین همه سینماها مشترکند"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration_minutes = models.PositiveIntegerField()
    poster = models.ImageField(upload_to='movies/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


# ==========================================
# بخش دوم: داده‌های ایزوله (Tenant Schema)
# ==========================================

class Hall(models.Model):
    """سالن سینما - مختص دیتابیس یک شعبه خاص"""
    name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name


class Seat(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='seats')
    row_label = models.CharField(max_length=5)
    seat_number = models.PositiveIntegerField()
    is_vip = models.BooleanField(default=False)

    class Meta:
        unique_together = ('hall', 'row_label', 'seat_number')

    def __str__(self):
        return f"{self.hall.name} : {self.row_label}{self.seat_number}"


class Showtime(models.Model):
    """سانس پخش فیلم"""
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE) # اشاره به جدول پابلیک
    start_time = models.DateTimeField()
    base_price = models.DecimalField(max_digits=10, decimal_places=0)

    def __str__(self):
        return f"{self.movie.title} | {self.hall.name} | {self.start_time.strftime('%Y-%m-%d %H:%M')}"


class ShowtimeSeat(models.Model):
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('RESERVED', 'Reserved (In Cart)'),
        ('SOLD', 'Sold')
    )
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name='showtime_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    
    class Meta:
        unique_together = ('showtime', 'seat')

    def __str__(self):
        return f"Showtime: {self.showtime.id} | Seat: {self.seat} - {self.get_status_display()}"