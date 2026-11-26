from rest_framework import serializers
from payments.models import Transaction


class PaymentRequestInputSerializer(serializers.Serializer):
    order_number = serializers.CharField(max_length=20)


class TransactionSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'transaction_id',
            'order_number',
            'order_status',
            'amount',
            'status',
            'gateway_name',
            'authority',
            'ref_id',
            'card_pan',
            'response_code',
            'response_message',
            'created_at',
        ]