from django.db import models

class Address(models.Model):
    """Independent address table for branches (and potentially users in the future)"""
    province = models.CharField(max_length=50, verbose_name="Province/State")
    city = models.CharField(max_length=50, verbose_name="City")
    full_address = models.TextField(verbose_name="Full Address")
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    
    # Coordinates for maps integration
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.province}, {self.city} - {self.full_address[:30]}"


class Cinema(models.Model):
    """The main brand or franchise (e.g., Kourosh Cineplex)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CinemaBranch(models.Model):
    """Physical branches belonging to a Cinema brand"""
    cinema = models.ForeignKey(Cinema, on_delete=models.CASCADE, related_name='branches')
    address = models.OneToOneField(Address, on_delete=models.PROTECT, related_name='cinema_branch')
    
    # Manager is the owner: A branch must have a manager to exist, and we protect it from accidental deletion
    manager = models.OneToOneField('profiles.Manager', on_delete=models.PROTECT, related_name='branch')
    
    branch_name = models.CharField(max_length=100) # e.g., "Main Branch", "West Branch"
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    
    # Store facilities like Parking, Cafe, WiFi as JSON
    facilities = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.cinema.name} - {self.branch_name}"


class Hall(models.Model):
    """Halls/Rooms inside a specific branch"""
    branch = models.ForeignKey(CinemaBranch, on_delete=models.CASCADE, related_name='halls')
    name = models.CharField(max_length=50) # e.g., "VIP Hall", "Hall 1"
    
    def __str__(self):
        return f"{self.branch.branch_name} - {self.name}"


class Seat(models.Model):
    """Physical seats inside a hall"""
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='seats')
    row_label = models.CharField(max_length=5) # e.g., "A", "B"
    seat_number = models.PositiveIntegerField() # e.g., 1, 2, 3
    is_vip = models.BooleanField(default=False)

    class Meta:
        # Prevents having two 'A1' seats in the same hall
        unique_together = ('hall', 'row_label', 'seat_number')

    def __str__(self):
        return f"{self.hall.name} : {self.row_label}{self.seat_number}"


class Movie(models.Model):
    """Movie details"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration_minutes = models.PositiveIntegerField()
    poster = models.ImageField(upload_to='movies/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Showtime(models.Model):
    """A specific screening of a movie in a hall at a given time"""
    branch = models.ForeignKey(CinemaBranch, on_delete=models.CASCADE, related_name='showtimes')
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    base_price = models.DecimalField(max_digits=10, decimal_places=0)

    def __str__(self):
        return f"{self.movie.title} | {self.branch.branch_name} | {self.start_time.strftime('%Y-%m-%d %H:%M')}"


class ShowtimeSeat(models.Model):
    """State of a specific seat for a specific showtime (Crucial for booking logic and preventing double-booking)"""
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('RESERVED', 'Reserved (In Cart)'),
        ('SOLD', 'Sold')
    )
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name='showtime_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    
    class Meta:
        # A seat can only have one status per showtime
        unique_together = ('showtime', 'seat')

    def __str__(self):
        return f"Showtime: {self.showtime.id} | Seat: {self.seat} - {self.get_status_display()}"