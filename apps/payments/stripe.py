import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from .strategies import PaymentStrategy

class StripeStrategy(PaymentStrategy):
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
    
    def get_provider_name(self):
        return 'stripe'
    
    def create_payment(self, order, payment_data=None):
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(float(order.total_amount) * 100),
                currency='usd',
                payment_method_types=['card'],
                metadata={
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'user_id': str(order.user_id)
                },
                description=f"Order #{order.order_number}"
            )
            
            return {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'provider': 'stripe',
                'status': payment_intent.status,
                'amount': payment_intent.amount / 100,
                'currency': payment_intent.currency
            }
        except Exception as e:
            raise ValidationError(f"Stripe payment creation failed: {str(e)}")
    
    def confirm_payment(self, payment, data=None):
        try:
            payment_intent = stripe.PaymentIntent.confirm(
                payment.transaction_id,
                payment_method=data.get('payment_method_id')
            )
            
            return {
                'status': payment_intent.status,
                'transaction_id': payment_intent.id,
                'provider': 'stripe',
                'amount': payment_intent.amount / 100,
                'currency': payment_intent.currency
            }
        except Exception as e:
            raise ValidationError(f"Stripe confirmation failed: {str(e)}")
    
    def verify_payment(self, payment):
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment.transaction_id)
            
            status_map = {
                'succeeded': 'success',
                'requires_payment_method': 'pending',
                'requires_confirmation': 'pending',
                'canceled': 'failed'
            }
            
            return {
                'status': status_map.get(payment_intent.status, 'pending'),
                'transaction_id': payment_intent.id,
                'provider': 'stripe',
                'amount': payment_intent.amount / 100,
                'currency': payment_intent.currency,
                'metadata': payment_intent.metadata
            }
        except Exception as e:
            raise ValidationError(f"Stripe verification failed: {str(e)}")
    
    def handle_webhook(self, payload, signature):
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            
            event_handlers = {
                'payment_intent.succeeded': self._handle_payment_success,
                'payment_intent.payment_failed': self._handle_payment_failed,
                'payment_intent.created': self._handle_payment_created
            }
            
            handler = event_handlers.get(event.type)
            if handler:
                return handler(event.data.object)
            
            return {'handled': False, 'event': event.type}
            
        except Exception as e:
            raise ValidationError(f"Webhook handling failed: {str(e)}")
    
    def _handle_payment_success(self, payment_intent):
        return {
            'event': 'payment_intent.succeeded',
            'transaction_id': payment_intent.id,
            'status': 'success',
            'order_id': payment_intent.metadata.get('order_id'),
            'metadata': payment_intent
        }
    
    def _handle_payment_failed(self, payment_intent):
        return {
            'event': 'payment_intent.payment_failed',
            'transaction_id': payment_intent.id,
            'status': 'failed',
            'order_id': payment_intent.metadata.get('order_id'),
            'metadata': payment_intent
        }
    
    def _handle_payment_created(self, payment_intent):
        return {
            'event': 'payment_intent.created',
            'transaction_id': payment_intent.id,
            'status': 'pending',
            'order_id': payment_intent.metadata.get('order_id'),
            'metadata': payment_intent
        }
    
    def refund_payment(self, payment, amount=None, reason=None):
        try:
            refund = stripe.Refund.create(
                payment_intent=payment.transaction_id,
                amount=int(float(amount) * 100) if amount else None,
                reason='requested_by_customer'
            )
            
            return {
                'success': True,
                'refund_id': refund.id,
                'amount': refund.amount / 100,
                'status': refund.status
            }
        except Exception as e:
            raise ValidationError(f"Stripe refund failed: {str(e)}")