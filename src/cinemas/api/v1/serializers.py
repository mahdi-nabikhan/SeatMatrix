from rest_framework import serializers
from profiles.models import Manager
from cinemas.models import Cinema
from profiles.api.v1.manager import serializers as manager_serializer
from django.db import transaction



class CinemaRegisterSerializer (serializers.ModelSerializer):
    manager = manager_serializer.ManagerRegisterSerializer()
    class Meta : 
        fields = '__all__'
        model = Cinema
        
    @transaction.atomic
    def create(self, validated_data):
        data = validated_data.pop('manager')
        manager = manager_serializer.ManagerRegisterSerializer().create(data)
        cinema = Cinema.objects.create(manager=manager,**validated_data)
        return cinema
    
    
    
class CinemaListSerializer (serializers.ModelSerializer):
    class Meta:
        model = Cinema
        fields = ['name','image','description','created_at']
        
        
        
        
class CinemaDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cinema
        fields ='__all__'
        
        
    def to_representation(self, instance):
        res =  super().to_representation(instance)
        res['manager'] = manager_serializer.ManagerDetailSerializer(instance.manager).data
        return res
    
    
    
    
class CinemaUpdateSerializer(serializers.ModelSerializer):
        class Meta:
            model = Cinema
            fields = ['name','image','description','created_at']
            read_only_fields = ['created_at']
    