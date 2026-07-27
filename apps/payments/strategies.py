from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    """Abstract base class for payment strategies"""
    
    @abstractmethod
    def get_provider_name(self):
        """Return the provider name"""
        pass
    
    @abstractmethod
    def create_payment(self, order, payment_data=None):
        """Create a payment for the order"""
        pass
    
    @abstractmethod
    def confirm_payment(self, payment, data=None):
        """Confirm an existing payment"""
        pass
    
    @abstractmethod
    def verify_payment(self, payment):
        """Verify payment status"""
        pass
    
    @abstractmethod
    def handle_webhook(self, payload, signature):
        """Handle webhook events"""
        pass
    
    def refund_payment(self, payment, amount=None, reason=None):
        """Refund a payment (optional)"""
        raise NotImplementedError("Refund not implemented for this provider")