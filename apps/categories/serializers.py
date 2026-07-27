from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    full_path = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent', 'level', 
                  'path', 'is_active', 'children', 'product_count', 'full_path', 'created_at']
        read_only_fields = ['id', 'slug', 'level', 'path', 'created_at']
    
    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data
    
    def get_product_count(self, obj):
        return obj.products.filter(status='active').count()
    
    def get_full_path(self, obj):
        return obj.path

class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'is_active']
    
    def validate(self, data):
        if data.get('parent'):
            # Prevent circular reference
            parent = data['parent']
            if parent.id == data.get('id'):
                raise serializers.ValidationError("Category cannot be its own parent")
        return data