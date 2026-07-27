from django.contrib import admin
from django.db import models
from django.forms import Textarea
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'stock', 'status', 'category', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['name', 'sku', 'description']
    list_editable = ['price', 'stock', 'status']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 40})},
    }
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sku', 'description', 'status')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock')
        }),
        ('Category & Images', {
            'fields': ('category', 'image_url')
        }),
        ('Additional Info', {
            'fields': ('weight', 'dimensions', 'metadata')
        }),
        ('System Fields', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )