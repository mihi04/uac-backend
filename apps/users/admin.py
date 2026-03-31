"""
apps/users/admin.py — Register User, Role, UserGroup, AuditLog in Django Admin.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Role, UserGroup, AuditLog,
    Screen, ScreenPermission, UserScreenOverride, UserGroupMembership,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['email', 'name', 'role', 'group', 'is_active', 'is_staff', 'created_at']
    list_filter   = ['is_active', 'is_staff', 'role']
    search_fields = ['email', 'name', 'employee_id']
    ordering      = ['email']
    fieldsets = (
        (None,            {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name', 'phone', 'profile_picture')}),
        ('Role & Group',  {'fields': ('role', 'group', 'employee_id')}),
        ('Permissions',   {'fields': ('is_active', 'is_staff', 'is_superuser',
                                      'groups', 'user_permissions')}),
        ('Dates',         {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'role', 'is_staff'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display  = ['name', 'description']
    search_fields = ['name']


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display  = ['name', 'status', 'created_at']
    list_filter   = ['status']
    search_fields = ['name']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ['table_name', 'action', 'changed_by', 'ip_address', 'changed_at']
    list_filter   = ['action', 'table_name']
    search_fields = ['table_name', 'endpoint']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ScreenPermissionInline(admin.TabularInline):
    model = ScreenPermission
    extra = 0


class UserGroupMembershipInline(admin.TabularInline):
    model = UserGroupMembership
    extra = 0
    fk_name = 'group'
    autocomplete_fields = ['user']


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'module', 'ordering', 'is_active']
    list_filter = ['module', 'is_active']
    search_fields = ['code', 'name']
    inlines = [ScreenPermissionInline]


@admin.register(ScreenPermission)
class ScreenPermissionAdmin(admin.ModelAdmin):
    list_display = ['group', 'screen', 'can_view', 'can_add', 'can_edit', 'can_delete',
                    'can_approve', 'can_reject', 'can_export', 'can_print']
    list_filter = ['group', 'screen']


@admin.register(UserScreenOverride)
class UserScreenOverrideAdmin(admin.ModelAdmin):
    list_display = ['user', 'screen', 'can_view', 'can_add', 'can_edit', 'can_delete']
    list_filter = ['screen']
    autocomplete_fields = ['user', 'screen']


@admin.register(UserGroupMembership)
class UserGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'added_at']
    list_filter = ['group']
    autocomplete_fields = ['user', 'group']
