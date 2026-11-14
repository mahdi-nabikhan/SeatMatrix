from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.conf import settings
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer,EmailJWTLoginSerializers
from profiles.models import Customer,Manager,Staff
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()

class UserRegistrationApiView(generics.GenericAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    queryset = User.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
       
        serializer.is_valid(raise_exception=True) 
        
    
        serializer.save()
        
        return Response(
            {'detail': 'کاربر با موفقیت ثبت‌نام شد.'}, 
            status=status.HTTP_201_CREATED
        )
        
        
        
        
class EmailJwtLoginApiView (TokenObtainPairView):
    serializer_class = EmailJWTLoginSerializers
    permission_classes = [permissions.AllowAny]
    
    
    def post(self, request, *args, **kwargs):
        redirect_url = None
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        data=serializer.validated_data
        access_token = data['access']
        refresh_token = data['refresh']
        
        if Manager.objects.filter(user=user).exists():
            redirect_url = 'manager'
            
        elif Staff.objects.filter(user=user).exists():
            redirect_url = 'staff'
            
        elif Customer.objects.filter(user=user).exists():
            redirect_url = 'customer'
            
            
        response = Response({'user_id': user.id,'redirect_url': redirect_url,}, status=status.HTTP_200_OK)
        response.set_cookie(
            key=settings.SIMPLE_JWT['AUTH_COOKIE'],
            value=access_token,
            max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
        )
        response.set_cookie(
            key=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
            value=refresh_token,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
        )

        return response
            
        