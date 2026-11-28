from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from profiles.models import Manager
from .serializers import ManagerRegisterSerializer, ManagerDetailSerializer




class ManagerRegisterApiView(generics.CreateAPIView):
    """Register a new cinema manager account along with its linked user credentials."""
    serializer_class = ManagerRegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    
    
    
class ManagerDetailApiView(generics.GenericAPIView):
    """Retrieve the authenticated user's Manager profile."""
    queryset =  Manager.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ManagerDetailSerializer
    
    
    def get_object(self):
        """Return the Manager profile for `request.user` or raise 404."""
        return  get_object_or_404(Manager,user=self.request.user)
    
    
    
    def get(self,request):
        """Return serialized Manager profile data."""
        obj = self.get_object()
        serializer = self.get_serializer(instance= obj , context= {'request':request})
        return Response(serializer.data , status=status.HTTP_200_OK)