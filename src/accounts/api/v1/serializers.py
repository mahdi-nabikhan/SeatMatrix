
from rest_framework import serializers, validators
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import ValidationError
from accounts.models import User



class UserRegistrations(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    class Meta :
        model = User
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}
        
        
    def validate(self, attrs):
        password1 = attrs.get('password')
        password2 = attrs.get('confirm_password')
        
        
        if password1 != password2 : 
            msg = _('password most be match')
            raise serializers.ValidationError(msg, code='invalid password')
        try:
            validate_password(password=password1)
                
        except ValidationError as e:
            raise serializers.ValidationError({'password':e.message})
        return attrs
        
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        return User.objects.cre