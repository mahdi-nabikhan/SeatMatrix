from rest_framework import serializers
from orders.models import Order, Ticket





class HoldSeatsInputSerializer(serializers.Serializer):
    
    
    
    showtime_id = serializers.IntegerField(min_value=1)
    showtime_seat_ids = serializers.ListField(
        child = serializers.IntegerField(min_value =1),
        min_length =1,
        max_length=10,
        allow_empty = False
    )
    
    
    
    def validate_showtime_seat_ids(self,value):
        return sorted(set(value))
    
    
    
    
class LiveSeatSerializer(serializers.Serializer):
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('RESERVED', 'Reserved'),
        ('RESERVED_BY_ME', 'Reserved by me'),
        ('SOLD', 'Sold'),
    )
    showtime_seat_id = serializers.IntegerField()
    row_label = serializers.CharField()
    seat_number = serializers.IntegerField()
    is_vip = serializers.BooleanField()
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    
    
    

class TicketSerializer(serializers.ModelSerializer):
    row_label = serializers.CharField(source ='showtime_seat.seat.row_label',read_only=True)
    seat_number = serializers.IntegerField(source = 'showtime_seat.seat.seat_number',read_only=True)
    is_vip = serializers.BooleanField(source='showtime_seat.seat.is_vip',read_only=True)
    
    
    class Meta:
        model = Ticket
        fields = [
            'id',
            'ticket_code',
            'price',
            'row_label',
            'seat_number',
            'is_vip',
            'created_at',
        ]
        read_only_fields = fields
    
    
    
    
class OrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    tickets = TicketSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'status',
            'status_display',
            'total_amount',
            'discount_amount',
            'final_amount',
            'created_at',
            'tickets',
        ]
        read_only_fields = fields