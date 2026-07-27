from django.urls import path
from .views import (
    ProductListView, ProductDetailView, ProductStockUpdateView,
    ProductCategoryView
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('<uuid:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('<uuid:pk>/stock/', ProductStockUpdateView.as_view(), name='product-stock'),
    path('category/<uuid:category_id>/', ProductCategoryView.as_view(), name='product-category'),
]