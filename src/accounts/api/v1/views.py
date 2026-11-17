from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.conf import settings
from django.contrib.auth import get_user_model
from .serializers import UserRegistrations,EmailJWTLoginSerializers,UsernameJwtLoginSerializers,VerifyOTPLoginSerializer,RequestOTPSerializer
from profiles.models import Customer,Manager,Staff
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()

class UserRegistrationApiView(generics.GenericAPIView):
    serializer_class = UserRegistrations
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
        simple_jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
        response.set_cookie(
            key=simple_jwt_settings.get('AUTH_COOKIE', 'access_token'),
            value=access_token,
            max_age=int(simple_jwt_settings.get('ACCESS_TOKEN_LIFETIME').total_seconds()),
            secure=simple_jwt_settings.get('AUTH_COOKIE_SECURE', False),
            httponly=simple_jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            samesite=simple_jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=simple_jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        )
        
        response.set_cookie(
            key=simple_jwt_settings.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
            value=refresh_token,
            max_age=int(simple_jwt_settings.get('REFRESH_TOKEN_LIFETIME').total_seconds()),
            secure=simple_jwt_settings.get('AUTH_COOKIE_SECURE', False),
            httponly=simple_jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            samesite=simple_jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=simple_jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        )

        return response
            
            
            


class UsernameJwtLoginAPIview(generics.GenericAPIView):
    serializer_class = UsernameJwtLoginSerializers
    permission_classes = [permissions.AllowAny]
    
    
    def post(self,request,*args,**kwargs):
        redirect_url = None
        serializer = self.get_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.user
        tokens = serializer.validated_data
        
        
        access_token = tokens['access']
        refresh_token = tokens['refresh']
        
        if Manager.objects.filter(user=user).exists():
            redirect_url = 'manager'
        elif Staff.objects.filter(user=user).exists():
            redirect_url = 'staff'
        elif Customer.objects.filter(user=user).exists():
            redirect_url = 'customer'
            
            
        response = Response({'user_id': user.id, 'redirect_url': redirect_url}, status=status.HTTP_200_OK)
        
        
        simple_jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
        
        
        response.set_cookie(
            key=simple_jwt_settings.get('AUTH_COOKIE', 'access_token'),
            value=access_token,
            max_age=int(simple_jwt_settings.get('ACCESS_TOKEN_LIFETIME').total_seconds()),
            secure=simple_jwt_settings.get('AUTH_COOKIE_SECURE', False),
            httponly=simple_jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            samesite=simple_jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=simple_jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        )
        
        
        response.set_cookie(
            key=simple_jwt_settings.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
            value=refresh_token,
            max_age=int(simple_jwt_settings.get('REFRESH_TOKEN_LIFETIME').total_seconds()),
            secure=simple_jwt_settings.get('AUTH_COOKIE_SECURE', False),
            httponly=simple_jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            samesite=simple_jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=simple_jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        )

        return response
        
        
        
        
        
        
class CheckUserLoginApiview(generics.GenericAPIView):
    
    
    
    def get(self,request):
        return Response({'detail':request.user.username})
    
    
    
    


class LogoutApiView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self,request,*args,**kwargs):
        
        response = Response({'detail': 'با موفقیت خارج شدید.'}, status=status.HTTP_200_OK)
        simple_jwt_settings = getattr(settings,'SIMPLE_JWT', {})
        response.delete_cookie(
            key=simple_jwt_settings.get('AUTH_COOKIE', 'access_token'),
            path=simple_jwt_settings.get('AUTH_COOKIE_PATH', '/'),
            samesite=simple_jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        )
        
        response.delete_cookie(
            key=simple_jwt_settings.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
            path=simple_jwt_settings.get('AUTH_COOKIE_PATH', '/'),
            samesite=simple_jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        )
        return response