from rest_framework import serializers
from .models import Product
from apps.categories.serializers import CategorySerializer

class ProductSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'description', 'price', 'stock', 'status',
                  'category', 'category_detail', 'image_url', 'weight', 'dimensions',
                  'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'price', 'stock', 'status', 
                  'category', 'image_url', 'weight', 'dimensions', 'metadata']
    
    def validate_sku(self, value):
        if Product.objects.filter(sku=value).exists():
            raise serializers.ValidationError("Product with this SKU already exists")
        return value

class ProductUpdateStockSerializer(serializers.Serializer):
    stock = serializers.IntegerField(min_value=0)