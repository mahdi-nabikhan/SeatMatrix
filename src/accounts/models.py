from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta




class CustomUserManager(BaseUserManager):
    """Custom manager for the User model using email as the primary identifier."""
    def create_user(self, username, email, password=None, **extra_fields):
        """Create and persist a standard user with a normalized email and hashed password.

        Args:
            username: Unique username for the account.
            email: Unique email address used for authentication.
            password: Raw password string to hash before saving.
            **extra_fields: Additional fields passed to the User model.

        Returns:
            The newly created User instance.

        Raises:
            ValueError: If username or email is missing.
        """
        if not username:
            raise ValueError('The Username field must be set')
        if not email:
            raise ValueError('The Email field must be set')
            
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create and persist a superuser with staff and superuser privileges enabled.

        Args:
            username: Unique username for the superuser.
            email: Unique email address for the superuser.
            password: Raw password string to hash before saving.
            **extra_fields: Additional fields passed to the User model.

        Returns:
            The newly created superuser instance.

        Raises:
            ValueError: If `is_staff` or `is_superuser` is explicitly set to False.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model authenticating via email with unique username and optional phone."""
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    
    # Optional phone number, unique if provided
    phone_number = models.CharField(
        max_length=15, 
        unique=True, 
        null=True, 
        blank=True
    )

    # Required fields for Django admin and authentication
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username','phone_number']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.username} ({self.email})"
    
    
    
    
    
    
    
class OTP(models.Model):
    """One-time password record used for phone-based authentication.

    Each code is valid for 2 minutes from creation and is invalidated once used.
    """
    user = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE, 
        related_name='otps'
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        """Return True if the OTP is unused and within its 2-minute validity window."""

        expiration_time = self.created_at + timedelta(minutes=2)
        return not self.is_used and timezone.now() <= expiration_time

    def __str__(self):
        return f"{self.user.username} : {self.code}"