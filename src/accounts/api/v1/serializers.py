
from rest_framework import serializers, validators
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
    """تابع کمکی برای تولید توکن‌های JWT"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'email': user.email,
        'username': user.username,
        'user_id': user.pk,
    }

class UserRegistrations(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    class Meta :
        model = User
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}
        
        
    def validate(self, attrs):
        password1 = attrs.get('password')
        password2 = attrs.get('confirm_password')
        phone_number = attrs.get('phone_number')
        
        if password1 != password2 : 
            msg = _('password most be match')
            raise serializers.ValidationError(msg, code='invalid password')
        
        if len(phone_number) <= 12:
             msg = _('password most be 12 charecter')
             raise serializers.ValidationError(msg, code='invalid password')
        
        try:
            validate_password(password=password1)
                
        except ValidationError as e:
            raise serializers.ValidationError({'password':e.message})
        return attrs
        
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        return User.objects.create_user(**self.validated_data)
    
    
    
    
    
class EmailJWTLoginSerializers(TokenObtainPairSerializer):
    " this is serializer for login with email and jwt "
    
    
    def validate(self, attrs):
        validated_data = super().validate(attrs)
        validated_data['email'] = self.user.email
        validated_data['user-id'] = self.user.pk
        return self.validate
    
    
    
    
class UsernameJwtLoginSerializers(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True,write_only=True)
    
    
    def validate(self, attrs):
        username= attrs.get('username')
        password=  attrs.get('password') 
        user= User.objects.filter(username=username).first()
        
        if not user or not user.check_password(password):
            raise serializers.ValidationError("نام کاربری یا رمز عبور اشتباه است.")
        return get_tokens_for_user(user)
       
       
       
       
class RequestOTPSerializer(serializers.Serializer):
    """ requst for sending a OTP code """
    phone_number = serializers.CharField(max_length=15, required=True)
    
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        user= User.objects.filter(phone_number=phone_number).first()
        if not user:
            raise serializers.ValidationError("کاربری با این شماره موبایل یافت نشد.")
        
        code = str(random.randint(100000, 999999))
        otp_obj = OTP.objects.create(user=user, code=code)
        attrs['otp_obj'] = otp_obj
        return attrs
    
    
    
class VerifyOTPLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15, required=True)
    code = serializers.CharField(max_length=6, required=True)
    
    
    
    def validate(self, attrs):
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

        return get_tokens_for_user(user)
    
    
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=255, required=True,write_only = True,trim_whitespace=False)
    new_password = serializers.CharField(write_only = True)
    confirm_password = serializers.CharField(write_only = True)
    
    def validate(self, data):
        user = self.context['request'].user
        old_password=data['old_password']
        new_password=data['new_password']
        new_password1 = data['new_password1']
        
        
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
            
        except ValidationError as e :
             raise serializers.ValidationError({
                "new_password": e.messages
            }) 
        return data

class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    """
    خواندن خودکار refresh_token از کوکی HttpOnly به جای بدنه درخواست JSON
    """
    # فیلد refresh را اختیاری می‌کنیم تا اگر در بادی فرستاده نشد، DRF خطای Required ندهد
    refresh = serializers.CharField(required=False)

    def extract_refresh_token(self):
        request = self.context.get('request')
        if request is not None:
            cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token')
            cookie_token = request.COOKIES.get(cookie_name)
            if cookie_token:
                return cookie_token
        raise InvalidToken("توکن رفرش در کوکی یافت نشد.")

    def validate(self, attrs):
        # اگر در بدنه JSON فرستاده نشده بود، از کوکی استخراج کن
        if not attrs.get('refresh'):
            attrs['refresh'] = self.extract_refresh_token()
            
        return super().validate(attrs)
        