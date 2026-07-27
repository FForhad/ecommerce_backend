from django.core.cache import cache
from django.db.models import Count
from .models import Category
from apps.products.models import Product
import logging

logger = logging.getLogger(__name__)

class CategoryService:
    CACHE_KEY = 'category_tree'
    CACHE_TTL = 3600  # 1 hour
    
    @classmethod
    def build_category_tree(cls, parent_id=None, depth=0, path=''):
        """Build category tree using DFS"""
        try:
            categories = Category.objects.filter(
                parent_id=parent_id,
                is_active=True
            ).order_by('name')
            
            tree = []
            
            for category in categories:
                current_path = f"{path} > {category.name}" if path else category.name
                category.level = depth
                category.path = current_path
                
                # Get product count
                product_count = Product.objects.filter(
                    category_id=category.id,
                    status='active'
                ).count()
                
                node = {
                    'id': str(category.id),
                    'name': category.name,
                    'slug': category.slug,
                    'description': category.description,
                    'level': depth,
                    'path': current_path,
                    'product_count': product_count,
                    'children': cls.build_category_tree(category.id, depth + 1, current_path),
                    'is_active': category.is_active,
                    'created_at': category.created_at
                }
                
                tree.append(node)
            
            return tree
            
        except Exception as e:
            logger.error(f"Error building category tree: {str(e)}")
            raise
    
    @classmethod
    def get_category_tree(cls, use_cache=True):
        """Get category tree with Redis caching"""
        try:
            if use_cache:
                cached = cache.get(cls.CACHE_KEY)
                if cached:
                    logger.info("Category tree retrieved from cache")
                    return cached
            
            logger.info("Building category tree from database")
            tree = cls.build_category_tree()
            
            if use_cache:
                cache.set(cls.CACHE_KEY, tree, cls.CACHE_TTL)
            
            return tree
            
        except Exception as e:
            logger.error(f"Error getting category tree: {str(e)}")
            return cls.build_category_tree()
    
    @classmethod
    def invalidate_cache(cls):
        """Invalidate category tree cache"""
        try:
            cache.delete(cls.CACHE_KEY)
            logger.info("Category tree cache invalidated")
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
    
    @classmethod
    def dfs_find_path(cls, tree, target_id, path=None):
        """DFS to find category path"""
        if path is None:
            path = []
        
        for node in tree:
            current_path = path + [node['id']]
            
            if node['id'] == target_id:
                return current_path
            
            if node['children']:
                result = cls.dfs_find_path(node['children'], target_id, current_path)
                if result:
                    return result
        
        return None
    
    @classmethod
    def dfs_get_subcategories(cls, tree, target_id):
        """DFS to get all subcategories"""
        result = []
        
        def search(nodes):
            for node in nodes:
                if node['id'] == target_id:
                    cls._collect_all_child_ids(node, result)
                    return True
                if node['children']:
                    if search(node['children']):
                        return True
            return False
        
        search(tree)
        return result
    
    @classmethod
    def _collect_all_child_ids(cls, node, result):
        """Collect all child category IDs"""
        result.append(node['id'])
        for child in node['children']:
            cls._collect_all_child_ids(child, result)
    
    @classmethod
    def get_recommended_products(cls, category_id, limit=10):
        """Get recommended products using DFS"""
        try:
            tree = cls.get_category_tree(use_cache=False)
            subcategory_ids = cls.dfs_get_subcategories(tree, str(category_id))
            
            if not subcategory_ids:
                # Get products from the same category
                products = Product.objects.filter(
                    category_id=category_id,
                    status='active'
                ).order_by('-created_at')[:limit]
                return products
            
            # Get products from all subcategories
            products = Product.objects.filter(
                category_id__in=subcategory_ids,
                status='active'
            ).order_by('-created_at')[:limit]
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting recommended products: {str(e)}")
            return []
    
    @classmethod
    def get_category_breadcrumbs(cls, category_id):
        """Get breadcrumb for a category"""
        try:
            tree = cls.get_category_tree(use_cache=False)
            path = cls.dfs_find_path(tree, str(category_id))
            
            if not path:
                return []
            
            breadcrumbs = []
            for cat_id in path:
                try:
                    category = Category.objects.get(id=cat_id)
                    breadcrumbs.append({
                        'id': str(category.id),
                        'name': category.name,
                        'slug': category.slug
                    })
                except Category.DoesNotExist:
                    continue
            
            return breadcrumbs
            
        except Exception as e:
            logger.error(f"Error getting category breadcrumbs: {str(e)}")
            return []