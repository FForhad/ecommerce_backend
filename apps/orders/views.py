from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import Order, OrderItem
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderItemSerializer
)
from apps.products.models import Product
from core.permissions import IsAuthenticated
from core.pagination import StandardResultsSetPagination
import logging

logger = logging.getLogger(__name__)

class OrderCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderCreateSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        items_data = validated_data['items']
        shipping_address = validated_data['shipping_address']
        billing_address = validated_data.get('billing_address', shipping_address)
        notes = validated_data.get('notes', '')
        coupon_code = validated_data.get('coupon_code', '')
        
        user = request.user
        
        # Generate order number
        order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{timezone.now().timestamp():.0f}-{user.id[:8]}"
        
        # Create order
        order = Order.objects.create(
            user=user,
            order_number=order_number,
            shipping_address=shipping_address,
            billing_address=billing_address,
            notes=notes,
            coupon_code=coupon_code,
            status='pending',
            payment_status='pending',
            total_amount=0,
            subtotal=0
        )
        
        total_amount = 0
        order_items = []
        
        # Create order items
        for item_data in items_data:
            try:
                product = Product.objects.select_for_update().get(id=item_data['product_id'])
                
                if product.stock < item_data['quantity']:
                    raise Exception(f"Insufficient stock for product: {product.name}")
                
                if product.status != 'active':
                    raise Exception(f"Product {product.name} is not active")
                
                price = float(product.price)
                quantity = item_data['quantity']
                subtotal = price * quantity
                total_amount += subtotal
                
                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price,
                    subtotal=subtotal
                )
                order_items.append(order_item)
                
            except Product.DoesNotExist:
                raise Exception(f"Product {item_data['product_id']} not found")
        
        # Update order total
        order.subtotal = total_amount
        order.total_amount = total_amount
        order.save()
        
        # Prepare response
        order_data = OrderSerializer(order).data
        order_data['items'] = OrderItemSerializer(order_items, many=True).data
        
        return Response({
            'success': True,
            'data': order_data
        }, status=status.HTTP_201_CREATED)

class OrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Order.objects.all().prefetch_related('items', 'items__product')
        return Order.objects.filter(user=user).prefetch_related('items', 'items__product')

class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Order.objects.all().prefetch_related('items', 'items__product')
        return Order.objects.filter(user=user).prefetch_related('items', 'items__product')

class OrderStatusView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        try:
            user = request.user
            if user.role == 'admin':
                order = Order.objects.get(id=pk)
            else:
                order = Order.objects.get(id=pk, user=user)
            
            return Response({
                'success': True,
                'data': {
                    'id': str(order.id),
                    'order_number': order.order_number,
                    'status': order.status,
                    'payment_status': order.payment_status,
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at,
                    'updated_at': order.updated_at
                }
            })
        except Order.DoesNotExist:
            return Response({
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)

class OrderCancelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, pk):
        try:
            user = request.user
            if user.role == 'admin':
                order = Order.objects.select_for_update().get(id=pk)
            else:
                order = Order.objects.select_for_update().get(id=pk, user=user)
            
            if order.status == 'paid':
                return Response({
                    'error': 'Cannot cancel a paid order'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if order.status == 'canceled':
                return Response({
                    'error': 'Order already canceled'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update order status
            order.status = 'canceled'
            order.save()
            
            # Restore stock
            for item in order.items.all():
                product = Product.objects.select_for_update().get(id=item.product_id)
                product.increase_stock(item.quantity)
            
            logger.info(f"Order {order.order_number} canceled by user {user.id}")
            
            return Response({
                'success': True,
                'message': 'Order canceled successfully',
                'data': OrderSerializer(order).data
            })
            
        except Order.DoesNotExist:
            return Response({
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Order cancellation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)