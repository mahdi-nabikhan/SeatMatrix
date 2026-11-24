from rest_framework import serializers
from profiles.models import Staff


class StaffSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = Staff
        fields = ['id', 'email', 'username', 'phone_number', 'shift', 'is_active']