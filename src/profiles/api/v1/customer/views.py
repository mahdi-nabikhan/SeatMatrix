from .serializers import (CustomerUpdateSerializer,CustomerRegisterSerializers,CustomerDetailSerializer)
from rest_framework import generics,status,permissions
from rest_framework.response import Response
from profiles.models import Customer
from django.shortcuts import get_object_or_404


class CustomerRegisterationApiView(generics.CreateAPIView):
    serializer_class = CustomerRegisterSerializers
    queryset = Customer.objects.all()
    permission_classes = [permissions.AllowAny]
    
    
    

class CustomerDetailAPIview(generics.GenericAPIView):
    serializer_class = CustomerDetailSerializer
    queryset = Customer.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    
    def get_object(self):
        return get_object_or_404(Customer, user=self.request.user)

    
    
    
    def get(self,request):
        data=self.get_object()
        serializer = self.get_serializer(instance=data,context={'request':request})
        return Response(serializer.data,status=status.HTTP_200_OK)
        
        
        
class CustomerUpdateApiView(generics.GenericAPIView):
    serializer_class = CustomerUpdateSerializer
    queryset = Customer.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    
    
    def get_object(self):
        return get_object_or_404(Customer, user=self.request.user)

    
    
    
    
    def put(self,request):
        obj = self.get_object()
        update_serializer = self.get_serializer(instance = obj,data =request.data)
        update_serializer.is_valid(raise_exception=True)
        update_serializer.save()
        return Response({'message':'update successfully'})
    
    
    
    def patch(self,request):
        obj = self.get_object()
        update_serializer = self.get_serializer(instance = obj,data =request.data,partial=True)
        update_serializer.is_valid(raise_exception=True)
        update_serializer.save()
        return Response({'message':'update successfully'})
    


class CustomerDeleteApiView(generics.GenericAPIView):
    
        def get_object(self):
            return get_object_or_404(Customer, user=self.request.user)
    
        def delete(self,request):
            obj = self.get_object()
            obj.delete()
            return Response({'message':'Delete successfully'})
    

