# flowerapp/permissions.py
from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    """
    Allows access only to users with role 'superadmin'.
    """

    def has_permission(self, request, view):
        # Check user is authenticated and has a profile
        if not request.user.is_authenticated:
            return False
        
        # Check if profile exists and role is superadmin
        return hasattr(request.user, 'profile') and request.user.profile.role == 'superadmin'
