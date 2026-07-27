from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'order', 'order_number', 'user', 'user_email', 'provider',
                  'transaction_id', 'amount', 'currency', 'status', 'raw_response',
                  'metadata', 'completed_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class PaymentInitiateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    provider = serializers.ChoiceField(choices=['stripe', 'bkash'])
    
    def validate_order_id(self, value):
        from apps.orders.models import Order
        try:
            order = Order.objects.get(id=value)
            if order.status == 'paid':
                raise serializers.ValidationError("Order already paid")
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found")
        return value

class PaymentConfirmSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['stripe', 'bkash'], required=False)
    payment_method_id = serializers.CharField(required=False)