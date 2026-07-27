from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product
from .serializers import ProductSerializer, ProductCreateSerializer, ProductUpdateStockSerializer
from apps.categories.services import CategoryService
from core.permissions import IsAuthenticated, IsAdmin
from core.pagination import StandardResultsSetPagination

class ProductListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category']
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['price', 'stock', 'created_at']
    
    def get_queryset(self):
        queryset = Product.objects.all()
        if not self.request.user.role == 'admin':
            queryset = queryset.filter(status='active')
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateSerializer
        return ProductSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        
        # Invalidate category cache if category assigned
        if product.category_id:
            CategoryService.invalidate_cache()
        
        return Response({
            'success': True,
            'data': ProductSerializer(product).data
        }, status=status.HTTP_201_CREATED)

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Product.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateSerializer
        return ProductSerializer
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get recommendations
        recommendations = []
        if instance.category_id:
            recommendations = CategoryService.get_recommended_products(
                instance.category_id, 5
            )
            recommendations = [p for p in recommendations if p.id != instance.id]
        
        from .serializers import ProductSerializer
        recommendations_data = ProductSerializer(recommendations, many=True).data
        
        return Response({
            'success': True,
            'data': {
                'product': serializer.data,
                'recommendations': recommendations_data
            }
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Invalidate category cache
        CategoryService.invalidate_cache()
        
        return Response({
            'success': True,
            'data': ProductSerializer(instance).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Product deleted successfully'
        }, status=status.HTTP_200_OK)

class ProductStockUpdateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ProductUpdateStockSerializer
    
    def patch(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product.stock = serializer.validated_data['stock']
        product.save()
        
        return Response({
            'success': True,
            'data': ProductSerializer(product).data
        })

class ProductCategoryView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, category_id):
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        offset = (page - 1) * limit
        
        products = Product.objects.filter(
            category_id=category_id,
            status='active'
        ).order_by('-created_at')
        
        total = products.count()
        products = products[offset:offset + limit]
        
        # Get breadcrumbs
        breadcrumbs = CategoryService.get_category_breadcrumbs(category_id)
        
        serializer = ProductSerializer(products, many=True)
        
        return Response({
            'success': True,
            'data': {
                'products': serializer.data,
                'breadcrumbs': breadcrumbs,
                'pagination': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': (total + limit - 1) // limit if total > 0 else 0
                }
            }
        })