from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from profiles.models import Manager
from .serializers import ManagerRegisterSerializer, ManagerDetailSerializer




class ManagerRegisterApiView(generics.CreateAPIView):
    serializer_class = ManagerRegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    
    
    
class ManagerDetailApiView(generics.GenericAPIView):
    queryset =  Manager.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ManagerDetailSerializer
    
    
    def get_object(self):
        return  get_object_or_404(Manager,user=self.request.user)
    
    
    
    def get(self,request):
        obj = self.get_object()
        serializer = self.get_serializer(instance= obj , context= {'request':request})
        return Response(serializer.data , status=status.HTTP_200_OK)