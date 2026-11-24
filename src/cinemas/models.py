from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.core.validators import FileExtensionValidator


class Cinema(TenantMixin):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    manager = models.OneToOneField(
        'profiles.Manager',
        on_delete=models.PROTECT,
        related_name='owned_cinema',
        null=True,
        blank=True
    )
    image = models.ImageField(upload_to='cinemas/images/', null=True, blank=True)
    auto_create_schema = True

    def __str__(self):
        if self.schema_name == 'public':
            return "Public Core System"
        return self.name


class CinemaDomain(DomainMixin):
    """آدرس دامنه یا ساب‌دامین اختصاصی هر سینما"""
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
    created_by_cinema = models.ForeignKey(
        'Cinema',
        on_delete=models.SET_NULL,null=True,blank=True,related_name='created_movies')

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
    
    
    
    
