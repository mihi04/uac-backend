"""
apps/users/permissions.py — RBAC permission classes.
"""

from rest_framework.permissions import BasePermission

ADMIN_ROLES = {'admin', 'super_admin'}
MANAGER_ROLES = {'manager', 'operations_manager', 'finance_manager'}


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        role = request.user.role_name
        return role in ADMIN_ROLES | MANAGER_ROLES


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.role_name in ADMIN_ROLES


class IsFinanceTeam(BasePermission):
    FINANCE_ROLES = {'admin', 'super_admin', 'accounts', 'finance_manager'}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.role_name in self.FINANCE_ROLES


class HasScreenPermission(BasePermission):
    """
    Generic screen-level permission check.
    Usage: set `screen_code` and `required_action` on the view, e.g.:
        screen_code = 'quotation'
        required_action = 'can_add'
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        screen_code = getattr(view, 'screen_code', None)
        required_action = getattr(view, 'required_action', 'can_view')
        if not screen_code:
            return True

        perms = user.get_effective_permissions(screen_code)
        return perms.get(required_action, False)
