from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer

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