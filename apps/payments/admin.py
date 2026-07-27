from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'user', 'provider', 'transaction_id', 'amount', 'status', 'created_at']
    list_filter = ['provider', 'status', 'created_at']
    search_fields = ['transaction_id', 'order__order_number', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('order', 'user', 'provider', 'transaction_id')
        }),
        ('Amount & Status', {
            'fields': ('amount', 'currency', 'status', 'completed_at')
        }),
        ('Raw Data', {
            'fields': ('raw_request', 'raw_response', 'metadata'),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_success', 'mark_as_failed']
    
    def mark_as_success(self, request, queryset):
        updated = queryset.update(status='success')
        self.message_user(request, f'{updated} payments marked as success.')
    mark_as_success.short_description = 'Mark selected payments as success'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} payments marked as failed.')
    mark_as_failed.short_description = 'Mark selected payments as failed'