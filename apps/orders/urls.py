from django.urls import path
from .views import (
    OrderCreateView, OrderListView, OrderDetailView,
    OrderCancelView, OrderStatusView
)

urlpatterns = [
    path('', OrderListView.as_view(), name='order-list'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('<uuid:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('<uuid:pk>/status/', OrderStatusView.as_view(), name='order-status'),
    path('<uuid:pk>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
]