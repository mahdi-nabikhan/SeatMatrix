from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator 

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
    image = models.ImageField(upload_to='cinemas/images/', null=True, blank=True)
    
    def __str__(self):
        return self.name


class CinemaBranch(TenantMixin):
    cinema = models.ForeignKey(Cinema, on_delete=models.CASCADE, related_name='branches', null=True, blank=True)
    address = models.OneToOneField(Address, on_delete=models.PROTECT, related_name='cinema_branch', null=True, blank=True)
    cover_image = models.ImageField(upload_to='branches/covers/', null=True, blank=True)
    branch_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    facilities = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    auto_create_schema = True

    def clean(self):
        super().clean()
        if self.schema_name != 'public':
            if not self.cinema:
                raise ValidationError({'cinema': 'تعیین سینما برای شعبه الزامی است.'})
            if not self.address:
                raise ValidationError({'address': 'ثبت آدرس برای شعبه الزامی است.'})

    def __str__(self):
        if self.schema_name == 'public':
            return "Public Core System"
        return f"{self.cinema.name} - {self.branch_name}"


class CinemaBranchImage(models.Model):
    """گالری تصاویر شعبه"""
    branch = models.ForeignKey(CinemaBranch, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='branches/gallery/')
    caption = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.branch.branch_name} - {self.caption or 'No Caption'}"


class BranchDomain(DomainMixin):
    """آدرس دامنه اختصاصی مستأجر"""
    pass


class Movie(models.Model):
    """فیلم‌ها عمومی هستند و بین همه سینماها مشترکند"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration_minutes = models.PositiveIntegerField()
    poster = models.ImageField(upload_to='movies/posters/', null=True, blank=True)
    
    trailer = models.FileField(
        upload_to='movies/trailers/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mkv', 'webm'])]
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class MovieImage(models.Model):
    """گالری تصاویر فیلم"""
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='movies/gallery/')
    caption = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.movie.title}"


# ==========================================
# بخش دوم: داده‌های ایزوله (Tenant Schema)
# ==========================================

class Hall(models.Model):
    """سالن سینما - مختص دیتابیس یک شعبه خاص (Tenant-Specific)"""
    HALL_TYPES = (
        ('STANDARD', 'استاندارد'),
        ('VIP', 'وی‌آی‌پی (VIP)'),
        ('IMAX', 'آیمکس (IMAX)'),
        ('3D', 'سه‌بعدی'),
    )
    
    name = models.CharField(max_length=50) 
    hall_type = models.CharField(max_length=20, choices=HALL_TYPES, default='STANDARD')
    image = models.ImageField(upload_to='halls/covers/', null=True, blank=True)
    capacity = models.PositiveIntegerField(help_text="تعداد کل صندلی‌های این سالن")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_hall_type_display()})"


class HallImage(models.Model):
    """گالری تصاویر اختصاصی برای هر سالن"""
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='halls/gallery/')
    caption = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.hall.name} - {self.caption or 'No Caption'}"


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
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE) 
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