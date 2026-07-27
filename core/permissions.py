from rest_framework import permissions

class IsAuthenticated(permissions.BasePermission):
    """Allows access only to authenticated users"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

class IsAdmin(permissions.BasePermission):
    """Allows access only to admin users"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

class IsOwnerOrAdmin(permissions.BasePermission):
    """Allows access if user is the owner or admin"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        return hasattr(obj, 'user') and obj.user == request.user