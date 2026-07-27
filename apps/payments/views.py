from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError
from .models import Payment
from .serializers import (
    PaymentSerializer, PaymentInitiateSerializer, PaymentConfirmSerializer
)
from .service import payment_service
from apps.orders.models import Order
from core.permissions import IsAuthenticated
import logging

logger = logging.getLogger(__name__)

class PaymentInitiateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentInitiateSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = payment_service.create_payment(
                order_id=serializer.validated_data['order_id'],
                provider_name=serializer.validated_data['provider'],
                payment_data=request.data.get('payment_data', {})
            )
            
            return Response({
                'success': True,
                'data': {
                    'payment': PaymentSerializer(result['payment']).data,
                    'result': result['result']
                }
            })
            
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Payment initiation error: {str(e)}")
            return Response({
                'error': 'Failed to initiate payment'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentConfirmView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentConfirmSerializer
    
    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = payment_service.confirm_payment(
                payment_id=pk,
                provider_name=serializer.validated_data.get('provider'),
                data=serializer.validated_data
            )
            
            return Response({
                'success': True,
                'data': {
                    'payment': PaymentSerializer(result['payment']).data,
                    'result': result['result']
                }
            })
            
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Payment confirmation error: {str(e)}")
            return Response({
                'error': 'Failed to confirm payment'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentVerifyView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        try:
            payment = Payment.objects.get(id=pk)
            
            # Check if user owns this payment or is admin
            if request.user != payment.user and request.user.role != 'admin':
                return Response({
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            result = payment_service.verify_payment(pk)
            
            return Response({
                'success': True,
                'data': result
            })
            
        except Payment.DoesNotExist:
            return Response({
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response({
                'error': 'Failed to verify payment'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentStatusView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            
            # Check if user owns this order or is admin
            if request.user != order.user and request.user.role != 'admin':
                return Response({
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            payment = Payment.objects.filter(order=order).first()
            
            if not payment:
                return Response({
                    'error': 'No payment found for this order'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'data': PaymentSerializer(payment).data
            })
            
        except Order.DoesNotExist:
            return Response({
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)

class PaymentHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Payment.objects.all().order_by('-created_at')
        return Payment.objects.filter(user=user).order_by('-created_at')

class PaymentWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, provider):
        try:
            payload = request.body
            signature = request.headers.get('stripe-signature') or request.headers.get('x-bkash-signature')
            
            result = payment_service.handle_webhook(provider, payload, signature)
            
            return Response({
                'success': True,
                'data': result
            })
            
        except ValidationError as e:
            logger.error(f"Webhook validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return Response({
                'error': 'Webhook processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)