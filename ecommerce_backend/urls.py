from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="E-commerce API",
        default_version='v1',
        description="E-commerce Ordering & Payment System API",
        contact=openapi.Contact(email="support@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/products/', include('apps.products.urls')),
    path('api/categories/', include('apps.categories.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/payments/', include('apps.payments.urls')),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Debug toolbar
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

# Add this to your main urls.py for webhook endpoints
from django.views.decorators.csrf import csrf_exempt
from apps.payments.views import PaymentWebhookView

# For Stripe webhook (public endpoint)
path('webhooks/stripe/', csrf_exempt(PaymentWebhookView.as_view()), 
     {'provider': 'stripe'}, name='stripe-webhook'),
path('webhooks/bkash/', csrf_exempt(PaymentWebhookView.as_view()), 
     {'provider': 'bkash'}, name='bkash-webhook'),