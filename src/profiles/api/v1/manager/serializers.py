from rest_framework import serializers
from django.db import transaction
from profiles.models import Manager
from accounts.api.v1 import serializers as account_serializers

class ManagerRegisterSerializer(serializers.ModelSerializer):
    """Atomically create a User account and its linked Manager profile."""
  
    user = account_serializers.UserRegistrations(write_only=True)
    
    class Meta:
        model = Manager

        fields = ['user', 'bank_iban']
        
    @transaction.atomic
    def create(self, validated_data):
        """Create the underlying User first, then attach the Manager profile."""
        user_data = validated_data.pop('user')
        user = account_serializers.UserRegistrations().create(user_data)
        manager = Manager.objects.create(user=user, **validated_data)
        return manager
    
    
    



class ManagerDetailSerializer(serializers.ModelSerializer):
    """Serialize Manager profile details with nested read-only user info."""
    class Meta:
        model = Manager
        fields = '__all__'
        read_only_fields = ['user']
        
    def to_representation(self, instance):
        """Replace the user ID with serialized email, username, and phone number."""
        representation = super().to_representation(instance)
        representation['user'] = account_serializers.UserDetailSerializer(instance.user).data
        return representation