from rest_framework import serializers
from profiles.models import Customer
from accounts.api.v1 import serializers as account_serializers
from django.db import transaction


class CustomerRegisterSerializers(serializers.ModelSerializer):
    user = account_serializers.UserRegistrations(write_only=True)
    
    class Meta :
        model = Customer
        fields = ['first_name,last_name','age','user']
   
        
        
    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = account_serializers.UserRegistrations().create(user_data)
        customer = Customer.objects.create(user=user, **validated_data)
        return customer
    
    
    
class CustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['user']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = account_serializers.UserDetailSerializer(instance.user).data
        return representation
    
    
    
class CustomerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model =Customer
        fields = ['first_name,last_name','age']
        
        
        
