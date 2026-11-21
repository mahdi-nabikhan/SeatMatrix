from django.db import models
from cinemas.models import Movie


class Address(models.Model):
    province = models.CharField(max_length=50, verbose_name="Province/State")
    city = models.CharField(max_length=50, verbose_name="City")
    full_address = models.TextField(verbose_name="Full Address")
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.province}, {self.city} - {self.full_address[:30]}"


class CinemaBranch(models.Model):
    address = models.OneToOneField(
        Address,
        on_delete=models.PROTECT,
        related_name='cinema_branch'
    )
    cover_image = models.ImageField(upload_to='branches/covers/', null=True, blank=True)
    branch_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    facilities = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.branch_name


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


class Hall(models.Model):
    """سالن سینما - متصل به یک شعبه خاص"""
    HALL_TYPES = (
        ('STANDARD', 'استاندارد'),
        ('VIP', 'وی‌آی‌پی (VIP)'),
        ('IMAX', 'آیمکس (IMAX)'),
        ('3D', 'سه‌بعدی'),
    )

    branch = models.ForeignKey(CinemaBranch, on_delete=models.CASCADE, related_name='halls')
    name = models.CharField(max_length=50)
    hall_type = models.CharField(max_length=20, choices=HALL_TYPES, default='STANDARD')
    image = models.ImageField(upload_to='halls/covers/', null=True, blank=True)
    capacity = models.PositiveIntegerField(help_text="تعداد کل صندلی‌های این سالن")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.branch.branch_name} - {self.name} ({self.get_hall_type_display()})"


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
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='showtimes')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='showtimes')
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