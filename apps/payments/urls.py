from django.urls import path
from .views import (
    PaymentInitiateView, PaymentConfirmView, PaymentVerifyView,
    PaymentStatusView, PaymentHistoryView, PaymentWebhookView
)

urlpatterns = [
    path('initiate/', PaymentInitiateView.as_view(), name='payment-initiate'),
    path('<uuid:pk>/confirm/', PaymentConfirmView.as_view(), name='payment-confirm'),
    path('<uuid:pk>/verify/', PaymentVerifyView.as_view(), name='payment-verify'),
    path('order/<uuid:order_id>/status/', PaymentStatusView.as_view(), name='payment-status'),
    path('history/', PaymentHistoryView.as_view(), name='payment-history'),
    path('webhook/<str:provider>/', PaymentWebhookView.as_view(), name='payment-webhook'),
]