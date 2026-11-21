from rest_framework import serializers
from profiles.models import Manager
from cinemas.models import Cinema
from cinemas.api.v1.serializers import CinemaDetailSerializer
from profiles.api.v1.manager import serializers as manager_serializer
from django.db import transaction
from rest_framework.exceptions import NotFound
from operations.models import *



class CinemaAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields ='__all__'
        
        
            

class CinemasBranchRegisterSerializer(serializers.ModelSerializer):
    address = CinemaAddressSerializer()

    class Meta:
        model = CinemaBranch
        fields = '__all__'
        read_only_fields = ['cinema']  

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user

        try:
            cinema = Cinema.objects.select_related('manager').get(manager__user=user)
        except Cinema.DoesNotExist:
            raise NotFound('سینمایی برای این مدیر یافت نشد.')

        address_data = validated_data.pop('address')
        address = Address.objects.create(**address_data)

        return CinemaBranch.objects.create(
            cinema=cinema,
            address=address,
            **validated_data
        )
        
        
        
class CinemaBranchDetailSerializers(serializers.ModelSerializer):
    class Meta: 
        model = CinemaBranch
        fields ='__all__'
        
    def to_representation(self, instance):
        res = super().to_representation(instance)
        res['address'] = CinemaAddressSerializer(instance.address).data
        res['cinema'] = CinemaDetailSerializer(instance.cinema).data
        return res
    
        
        
class CinemaBranchUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaBranch
        fields = ['phone_number','branch_name','facilities','cover_image']
        
        
        
        


class CinemaBranchImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaBranchImage
        fields = ['id', 'branch', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def validate_branch(self, value):
        user = self.context['request'].user
        if value.cinema.manager.user != user:
            raise serializers.ValidationError('شما اجازه افزودن تصویر به این شعبه را ندارید.')
        return value


class CinemaBranchImageUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaBranchImage
        fields = ['id', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

        
        
