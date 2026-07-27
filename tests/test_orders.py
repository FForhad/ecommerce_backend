import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.products.models import Product

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )

@pytest.fixture
def product():
    return Product.objects.create(
        name='Test Product',
        sku='TEST001',
        price=99.99,
        stock=10,
        status='active'
    )

@pytest.mark.django_db
class TestOrderAPI:
    
    def test_create_order(self, api_client, user, product):
        api_client.force_authenticate(user=user)
        
        url = reverse('order-create')
        data = {
            'items': [
                {
                    'product_id': str(product.id),
                    'quantity': 2
                }
            ],
            'shipping_address': {
                'street': '123 Main St',
                'city': 'Dhaka',
                'country': 'Bangladesh',
                'postal_code': '1200'
            }
        }
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['data']['total_amount'] == 199.98
    
    def test_order_list(self, api_client, user):
        api_client.force_authenticate(user=user)
        
        url = reverse('order-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data