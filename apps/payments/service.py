from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Payment
from .stripe import StripeStrategy
from .bkash import BkashStrategy
from apps.orders.models import Order
from apps.products.models import Product
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        self.providers = {
            'stripe': StripeStrategy(),
            'bkash': BkashStrategy()
        }
    
    def get_provider(self, provider_name):
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValidationError(f"Payment provider {provider_name} not supported")
        return provider
    
    @transaction.atomic
    def create_payment(self, order_id, provider_name, payment_data=None):
        """Create a payment for an order"""
        try:
            # Get the order
            order = Order.objects.select_for_update().get(id=order_id)
            
            if order.status == 'paid':
                raise ValidationError("Order already paid")
            
            # Get the payment strategy
            strategy = self.get_provider(provider_name)
            
            # Create payment with provider
            result = strategy.create_payment(order, payment_data)
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                user=order.user,
                provider=provider_name,
                transaction_id=result.get('transaction_id') or result.get('payment_id'),
                amount=order.total_amount,
                currency=result.get('currency', 'BDT'),
                status='pending',
                raw_request=payment_data,
                metadata=result
            )
            
            # Update order
            order.payment_method = provider_name
            order.payment_status = 'pending'
            order.save()
            
            return {
                'payment': payment,
                'result': result,
                'order': order
            }
            
        except Order.DoesNotExist:
            raise ValidationError("Order not found")
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}")
            raise
    
    @transaction.atomic
    def confirm_payment(self, payment_id, provider_name=None, data=None):
        """Confirm a payment"""
        try:
            payment = Payment.objects.select_for_update().get(id=payment_id)
            provider = provider_name or payment.provider
            strategy = self.get_provider(provider)
            
            result = strategy.confirm_payment(payment, data)
            
            if result.get('status') == 'success':
                payment.mark_success(result)
                self._handle_successful_payment(payment.order_id)
            else:
                payment.mark_failed(result)
                self._handle_failed_payment(payment.order_id)
            
            return {
                'payment': payment,
                'result': result
            }
            
        except Payment.DoesNotExist:
            raise ValidationError("Payment not found")
        except Exception as e:
            logger.error(f"Payment confirmation error: {str(e)}")
            raise
    
    def _handle_successful_payment(self, order_id):
        """Handle post-payment success actions"""
        try:
            order = Order.objects.select_for_update().get(id=order_id)
            
            # Update order status
            order.status = 'paid'
            order.payment_status = 'success'
            order.save()
            
            # Reduce stock for each product
            for item in order.items.all():
                product = Product.objects.select_for_update().get(id=item.product_id)
                product.reduce_stock(item.quantity)
            
            logger.info(f"Order {order.order_number} payment successful, stock reduced")
            
        except Exception as e:
            logger.error(f"Error handling successful payment: {str(e)}")
            raise
    
    def _handle_failed_payment(self, order_id):
        """Handle failed payment"""
        try:
            order = Order.objects.select_for_update().get(id=order_id)
            order.status = 'canceled'
            order.payment_status = 'failed'
            order.save()
            logger.info(f"Order {order.order_number} payment failed, order canceled")
        except Exception as e:
            logger.error(f"Error handling failed payment: {str(e)}")
            raise
    
    def verify_payment(self, payment_id):
        """Verify payment status"""
        try:
            payment = Payment.objects.get(id=payment_id)
            strategy = self.get_provider(payment.provider)
            return strategy.verify_payment(payment)
        except Payment.DoesNotExist:
            raise ValidationError("Payment not found")
    
    def handle_webhook(self, provider_name, payload, signature):
        """Handle webhook events"""
        try:
            strategy = self.get_provider(provider_name)
            result = strategy.handle_webhook(payload, signature)
            
            if result and result.get('order_id'):
                self._process_webhook_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Webhook handling error: {str(e)}")
            raise
    
    def _process_webhook_result(self, result):
        """Process webhook result and update order/payment"""
        try:
            with transaction.atomic():
                order = Order.objects.get(order_number=result['order_id'])
                payment = Payment.objects.get(order=order)
                
                if result['status'] == 'success':
                    payment.mark_success(result['metadata'])
                    self._handle_successful_payment(order.id)
                else:
                    payment.mark_failed(result['metadata'])
                    self._handle_failed_payment(order.id)
                
                return {'order': order, 'payment': payment}
                
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            raise

payment_service = PaymentService()