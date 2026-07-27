from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .service import payment_service
from apps.orders.models import Order
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_payment_webhook(provider, payload, signature):
    """Process payment webhook asynchronously"""
    try:
        result = payment_service.handle_webhook(provider, payload, signature)
        logger.info(f"Webhook processed for provider {provider}: {result}")
        return result
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        raise

@shared_task
def send_payment_confirmation_email(order_id, payment_id):
    """Send payment confirmation email"""
    try:
        order = Order.objects.get(id=order_id)
        payment = order.payments.get(id=payment_id)
        user = order.user
        
        subject = f"Payment Confirmation - Order #{order.order_number}"
        message = f"""
        Dear {user.full_name},
        
        Your payment of {payment.amount} {payment.currency} has been confirmed.
        Order Number: {order.order_number}
        Payment Method: {payment.provider}
        Transaction ID: {payment.transaction_id}
        
        Thank you for your purchase!
        
        Best regards,
        E-commerce Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
        
        logger.info(f"Payment confirmation email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send payment confirmation email: {str(e)}")
        return False

@shared_task
def update_order_status_after_delivery(order_id):
    """Update order status after delivery delay"""
    try:
        order = Order.objects.get(id=order_id)
        if order.status == 'shipped':
            order.status = 'delivered'
            order.save()
            logger.info(f"Order {order.order_number} marked as delivered")
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
    except Exception as e:
        logger.error(f"Failed to update order status: {str(e)}")

@shared_task
def process_refund(payment_id, amount=None, reason=None):
    """Process refund asynchronously"""
    try:
        from .models import Payment
        payment = Payment.objects.get(id=payment_id)
        result = payment_service.get_provider(payment.provider).refund_payment(
            payment, amount, reason
        )
        
        if result.get('success'):
            payment.status = 'refunded'
            payment.save()
            
            # Send refund confirmation email
            send_payment_confirmation_email.delay(payment.order_id, payment_id)
            
        return result
    except Exception as e:
        logger.error(f"Refund processing failed: {str(e)}")
        raise

@shared_task
def verify_pending_payments():
    """Verify pending payments periodically"""
    from .models import Payment
    from django.utils import timezone
    from datetime import timedelta
    
    # Get payments pending for more than 30 minutes
    cutoff = timezone.now() - timedelta(minutes=30)
    pending_payments = Payment.objects.filter(
        status='pending',
        created_at__lt=cutoff
    )
    
    for payment in pending_payments:
        try:
            result = payment_service.verify_payment(payment.id)
            if result.get('status') == 'success':
                payment.mark_success(result)
                payment_service._handle_successful_payment(payment.order_id)
                send_payment_confirmation_email.delay(payment.order_id, payment.id)
            elif result.get('status') == 'failed':
                payment.mark_failed(result.get('error', 'Verification failed'))
                payment_service._handle_failed_payment(payment.order_id)
        except Exception as e:
            logger.error(f"Failed to verify payment {payment.id}: {str(e)}")