
from rest_framework import serializers, validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer,TokenRefreshSerializer
from rest_framework.exceptions import ValidationError
from accounts.models import User
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken
from django.contrib.auth import get_user_model
from ...models import OTP
import random

User = get_user_model()


def get_tokens_for_user(user):
    """Generate a JWT access/refresh token pair and basic user metadata.

    Args:
        user: Authenticated User instance.

    Returns:
        A dict containing `refresh`, `access`, `email`, `username`, and `user_id`.
    """
    
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'email': user.email,
        'username': user.username,
        'user_id': user.pk,
    }

class UserRegistrations(serializers.ModelSerializer):
    """Validate and register a new user account.

    Enforces password confirmation match, Django password strength validators,
    and a minimum 12-character phone number format.
    """
    
    confirm_password = serializers.CharField(write_only=True)
    class Meta :
        model = User
        fields = ['username','email','password','confirm_password','phone_number']
        extra_kwargs = {'password': {'write_only': True}}
        
        
    def validate(self, attrs):
        """Validate password match, phone number length, and password strength."""
        password1 = attrs.get('password')
        password2 = attrs.get('confirm_password')
        phone_number = attrs.get('phone_number')
        
        if password1 != password2 : 
            msg = _('password most be match')
            raise serializers.ValidationError(msg, code='invalid password')
        
        if len(phone_number) < 12:
             msg = _('Phone number must be at least 12 characters.')
             raise serializers.ValidationError(msg, code='invalid_phone_number')
        
        try:
            validate_password(password=password1)
                
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return attrs
        
    def create(self, validated_data):
        """Strip `confirm_password` and create the user via `create_user`."""
        validated_data.pop('confirm_password')
        return User.objects.create_user(**validated_data)
    
    
    
    
    
class EmailJWTLoginSerializers(TokenObtainPairSerializer):
    """Authenticate a user with email and password and attach user metadata to JWT output."""
    
    def validate(self, attrs):
        """Validate credentials and append `email` and `user-id` to the token payload."""
        validated_data = super().validate(attrs)
        validated_data['email'] = self.user.email
        validated_data['user-id'] = self.user.pk
        return validated_data
    
    
    
    
class UsernameJwtLoginSerializers(serializers.Serializer):
    """Authenticate an active user via username and password and issue JWT tokens."""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True,write_only=True)
    
    
    def validate(self, attrs):
        """Verify username/password pair and return generated JWT tokens."""
        username= attrs.get('username')
        password=  attrs.get('password') 
        user= User.objects.filter(username=username).first()
        
        if not user or not user.check_password(password):
            raise serializers.ValidationError("نام کاربری یا رمز عبور اشتباه است.")
        self.user= user
        return get_tokens_for_user(user)
       
       
       
       
class RequestOTPSerializer(serializers.Serializer):
    """Validate a phone number and generate a 6-digit OTP for the matching user."""
    phone_number = serializers.CharField(max_length=15, required=True)
    
    
    def validate(self, attrs):
        """Look up the user by phone number and persist a fresh OTP instance."""
        phone_number = attrs.get('phone_number')
        user= User.objects.filter(phone_number=phone_number).first()
        if not user:
            raise serializers.ValidationError("کاربری با این شماره موبایل یافت نشد.")
        
        code = str(random.randint(100000, 999999))
        otp_obj = OTP.objects.create(user=user, code=code)
        attrs['otp_obj'] = otp_obj
        return attrs
    
    
    
class VerifyOTPLoginSerializer(serializers.Serializer):
    """Verify an unused, non-expired OTP code and issue JWT tokens for the user."""
    phone_number = serializers.CharField(max_length=15, required=True)
    code = serializers.CharField(max_length=6, required=True)
    
    
    
    def validate(self, attrs):
        """Validate the OTP, mark it as used, and return JWT tokens."""
        phone_number = attrs.get('phone_number')
        code = attrs.get('code')
        user= User.objects.filter(phone_number=phone_number).first()
        
        
        if not user:
            raise serializers.ValidationError("کاربری با این شماره موبایل یافت نشد.")
        
        otp_obj = OTP.objects.filter(user=user, code=code, is_used=False).last()
        if not otp_obj or not otp_obj.is_valid():
            raise serializers.ValidationError("کد تایید نامعتبر یا منقضی شده است.")
        otp_obj.is_used = True
        otp_obj.save()
        self.user = user
        return get_tokens_for_user(user)
    
    
    
class ChangePasswordSerializer(serializers.Serializer):
    """Validate an authenticated user's password change request."""
    old_password = serializers.CharField(max_length=255, required=True,write_only = True,trim_whitespace=False)
    new_password = serializers.CharField(write_only = True)
    confirm_password = serializers.CharField(write_only = True)
    
    def validate(self, data):
        """Ensure old password is correct and new password is distinct, matching, and strong."""
        user = self.context['request'].user
        old_password=data['old_password']
        new_password=data['new_password']
        new_password1 = data['confirm_password']
        
        
        if not user.check_password(old_password):
            raise serializers.ValidationError({
                'old_password':'Your current password is incorrect.'
            })
        
        if new_password != new_password1:
            raise serializers.ValidationError({
                "new_password1": _("Passwords do not match.")
            })
            
        if old_password == new_password :
             raise serializers.ValidationError({
                "new_password": _("New password must be different from the current password.")
            })
        try:
            validate_password(password=new_password,user=user)
            
        except DjangoValidationError as e :
             raise serializers.ValidationError({
                "new_password": e.list(e.messages)
            }) 
        return data

class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    """Refresh JWT access tokens by reading the refresh token from HttpOnly cookies."""

    refresh = serializers.CharField(required=False)

    def extract_refresh_token(self):
        """Extract the refresh token from the incoming request's cookies.

        Returns:
            The raw refresh token string.

        Raises:
            InvalidToken: If the refresh cookie is missing from the request.
        """
        request = self.context.get('request')
        if request is not None:
            cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token')
            cookie_token = request.COOKIES.get(cookie_name)
            if cookie_token:
                return cookie_token
        raise InvalidToken("توکن رفرش در کوکی یافت نشد.")

    def validate(self, attrs):
        """Fallback to the refresh cookie when `refresh` is omitted from the request body."""
        if not attrs.get('refresh'):
            attrs['refresh'] = self.extract_refresh_token()
            
        return super().validate(attrs)
        
        
        
        
        
class UserDetailSerializer(serializers.ModelSerializer):
    """Expose basic read-only profile identifiers for a User instance."""
    class Meta :
        model = User
        fields =['email','phone_number','username']
        