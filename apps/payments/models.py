import uuid
from django.db import models
from apps.users.models import User
from apps.orders.models import Order

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    PROVIDER_CHOICES = (
        ('stripe', 'Stripe'),
        ('bkash', 'bKash'),
    )
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES)
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='BDT')
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    
    raw_request = models.JSONField(null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['provider', 'status']),
        ]
    
    def __str__(self):
        return f"{self.provider} - {self.transaction_id}"
    
    def mark_success(self, response):
        self.status = 'success'
        self.raw_response = response
        self.completed_at = models.DateTimeField.now()
        self.save()
        return self
    
    def mark_failed(self, error):
        self.status = 'failed'
        self.raw_response = {'error': str(error)}
        self.save()
        return self