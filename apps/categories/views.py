from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.core.cache import cache
from .models import Category
from .serializers import CategorySerializer, CategoryCreateSerializer
from .services import CategoryService
from core.permissions import IsAuthenticated, IsAdmin

class CategoryTreeView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        use_cache = request.query_params.get('cache', 'true').lower() == 'true'
        tree = CategoryService.get_category_tree(use_cache=use_cache)
        return Response({
            'success': True,
            'data': tree
        })

class CategoryListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CategoryCreateSerializer
        return CategorySerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        
        # Invalidate cache
        CategoryService.invalidate_cache()
        
        return Response({
            'success': True,
            'data': CategorySerializer(category).data
        }, status=status.HTTP_201_CREATED)

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CategoryCreateSerializer
        return CategorySerializer
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get breadcrumbs
        breadcrumbs = CategoryService.get_category_breadcrumbs(instance.id)
        
        return Response({
            'success': True,
            'data': {
                'category': serializer.data,
                'breadcrumbs': breadcrumbs
            }
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Invalidate cache
        CategoryService.invalidate_cache()
        
        return Response({
            'success': True,
            'data': CategorySerializer(instance).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        
        # Invalidate cache
        CategoryService.invalidate_cache()
        
        return Response({
            'success': True,
            'message': 'Category deleted successfully'
        }, status=status.HTTP_200_OK)

class CategoryRecommendationsView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, category_id):
        limit = int(request.query_params.get('limit', 10))
        products = CategoryService.get_recommended_products(category_id, limit)
        
        from apps.products.serializers import ProductSerializer
        serializer = ProductSerializer(products, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })