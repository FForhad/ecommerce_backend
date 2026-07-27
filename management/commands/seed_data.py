from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.users.models import User
from apps.categories.models import Category
from apps.products.models import Product
import random
import uuid

class Command(BaseCommand):
    help = 'Seed database with sample data'
    
    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        
        # Create categories
        categories = self.create_categories()
        
        # Create products
        self.create_products(categories)
        
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
    
    def create_categories(self):
        categories = []
        
        # Main categories
        main_categories = [
            {'name': 'Electronics', 'description': 'Electronic devices and accessories'},
            {'name': 'Clothing', 'description': 'Fashion and apparel'},
            {'name': 'Books', 'description': 'Books and publications'},
            {'name': 'Home & Garden', 'description': 'Home improvement and garden supplies'},
        ]
        
        for cat_data in main_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'is_active': True
                }
            )
            categories.append(category)
        
        # Subcategories for Electronics
        electronics = categories[0]
        sub_categories = [
            {'name': 'Laptops', 'description': 'Laptops and notebooks', 'parent': electronics},
            {'name': 'Smartphones', 'description': 'Mobile phones', 'parent': electronics},
            {'name': 'Accessories', 'description': 'Electronic accessories', 'parent': electronics},
        ]
        
        for cat_data in sub_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'parent': cat_data['parent'],
                    'is_active': True
                }
            )
            categories.append(category)
        
        return categories
    
    def create_products(self, categories):
        product_data = [
            {
                'name': 'Gaming Laptop Pro',
                'sku': f'LAP-{uuid.uuid4().hex[:8].upper()}',
                'description': 'High-performance gaming laptop with RTX 3080',
                'price': 1499.99,
                'stock': 25,
                'category': categories[1] if len(categories) > 1 else None,
            },
            {
                'name': 'Ultrabook Slim',
                'sku': f'LAP-{uuid.uuid4().hex[:8].upper()}',
                'description': 'Ultra-light laptop for professionals',
                'price': 899.99,
                'stock': 50,
                'category': categories[1] if len(categories) > 1 else None,
            },
            {
                'name': 'Smartphone X Pro',
                'sku': f'PHN-{uuid.uuid4().hex[:8].upper()}',
                'description': 'Latest flagship smartphone with 5G',
                'price': 1099.99,
                'stock': 75,
                'category': categories[2] if len(categories) > 2 else None,
            },
            {
                'name': 'Wireless Headphones',
                'sku': f'ACC-{uuid.uuid4().hex[:8].upper()}',
                'description': 'Premium wireless noise-canceling headphones',
                'price': 199.99,
                'stock': 100,
                'category': categories[3] if len(categories) > 3 else None,
            },
        ]
        
        for data in product_data:
            product, created = Product.objects.get_or_create(
                sku=data['sku'],
                defaults={
                    'name': data['name'],
                    'description': data['description'],
                    'price': data['price'],
                    'stock': data['stock'],
                    'category': data['category'],
                    'status': 'active'
                }
            )
            if created:
                self.stdout.write(f"Created product: {product.name}")