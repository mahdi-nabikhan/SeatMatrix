from .serializers import (CustomerUpdateSerializer,CustomerRegisterSerializers,CustomerDetailSerializer)
from rest_framework import generics,status,permissions
from rest_framework.response import Response
from profiles.models import Customer
from django.shortcuts import get_object_or_404


class CustomerRegisterationApiView(generics.CreateAPIView):
    """Register a new customer account along with its linked user credentials."""
    serializer_class = CustomerRegisterSerializers
    queryset = Customer.objects.all()
    permission_classes = [permissions.AllowAny]
    
    
    

class CustomerDetailAPIview(generics.GenericAPIView):
    """Retrieve the authenticated user's Customer profile."""
    serializer_class = CustomerDetailSerializer
    queryset = Customer.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    
    def get_object(self):
        """Return the Customer profile for `request.user` or raise 404."""
        return get_object_or_404(Customer, user=self.request.user)

    
    
    
    def get(self,request):
        """Return serialized Customer profile data."""
        data=self.get_object()
        serializer = self.get_serializer(instance=data,context={'request':request})
        return Response(serializer.data,status=status.HTTP_200_OK)
        
        
        
class CustomerUpdateApiView(generics.GenericAPIView):
    """Update the authenticated user's Customer profile via PUT or PATCH."""
    serializer_class = CustomerUpdateSerializer
    queryset = Customer.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    
    
    def get_object(self):
        """Return the Customer profile for `request.user` or raise 404."""
        return get_object_or_404(Customer, user=self.request.user)

    
    
    
    
    def put(self,request):
        """Perform a full update of the Customer profile."""
        obj = self.get_object()
        update_serializer = self.get_serializer(instance = obj,data =request.data)
        update_serializer.is_valid(raise_exception=True)
        update_serializer.save()
        return Response({'message':'update successfully'})
    
    
    
    def patch(self,request):
        """Perform a partial update of the Customer profile."""
        obj = self.get_object()
        update_serializer = self.get_serializer(instance = obj,data =request.data,partial=True)
        update_serializer.is_valid(raise_exception=True)
        update_serializer.save()
        return Response({'message':'update successfully'})
    


class CustomerDeleteApiView(generics.GenericAPIView):
        """Delete the authenticated user's Customer profile."""
        def get_object(self):
            """Return the Customer profile for `request.user` or raise 404."""
            return get_object_or_404(Customer, user=self.request.user)
    
        def delete(self,request):
            
            """Delete the current user's Customer profile record."""
            obj = self.get_object()
            obj.delete()
            return Response({'message':'Delete successfully'})
    

