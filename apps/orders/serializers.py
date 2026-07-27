from rest_framework import serializers
from .models import Order, OrderItem
from apps.products.serializers import ProductSerializer
from apps.users.serializers import UserSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_detail', 'quantity', 'price', 'subtotal']

class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_detail = UserSerializer(source='user', read_only=True)
    total_amount_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'user_detail', 'status', 'payment_status',
                  'total_amount', 'total_amount_formatted', 'subtotal', 'tax', 'shipping_cost',
                  'discount_amount', 'shipping_address', 'billing_address', 'payment_method',
                  'notes', 'coupon_code', 'items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']
    
    def get_total_amount_formatted(self, obj):
        return f"${float(obj.total_amount):.2f}"

class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemCreateSerializer(many=True)
    shipping_address = serializers.DictField()
    billing_address = serializers.DictField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")
        return value
    
    def validate_shipping_address(self, value):
        required_fields = ['street', 'city', 'country', 'postal_code']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"{field} is required in shipping address")
        return value