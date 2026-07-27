from django.urls import path
from .views import (
    CategoryTreeView, CategoryListView, CategoryDetailView,
    CategoryRecommendationsView
)

urlpatterns = [
    path('tree/', CategoryTreeView.as_view(), name='category-tree'),
    path('', CategoryListView.as_view(), name='category-list'),
    path('<uuid:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('<uuid:category_id>/recommendations/', CategoryRecommendationsView.as_view(), name='category-recommendations'),
]