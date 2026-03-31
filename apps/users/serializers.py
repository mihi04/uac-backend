"""
apps/users/serializers.py
"""

from rest_framework import serializers
from .models import (
    User, Role, UserGroup, Screen,
    ScreenPermission, UserScreenOverride, UserGroupMembership,
)


# ── Role ──────────────────────────────────────────────────────────────────────
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'


# ── Screen ────────────────────────────────────────────────────────────────────
class ScreenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screen
        fields = ['id', 'code', 'name', 'module', 'ordering', 'is_active']


# ── ScreenPermission ──────────────────────────────────────────────────────────
class ScreenPermissionSerializer(serializers.ModelSerializer):
    screen_code = serializers.CharField(source='screen.code', read_only=True)
    screen_name = serializers.CharField(source='screen.name', read_only=True)

    class Meta:
        model = ScreenPermission
        fields = [
            'id', 'group', 'screen', 'screen_code', 'screen_name',
            'can_view', 'can_add', 'can_edit', 'can_delete',
            'can_approve', 'can_reject', 'can_export', 'can_print',
        ]


class ScreenPermissionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreenPermission
        fields = [
            'screen',
            'can_view', 'can_add', 'can_edit', 'can_delete',
            'can_approve', 'can_reject', 'can_export', 'can_print',
        ]


# ── UserGroup ─────────────────────────────────────────────────────────────────
class UserGroupListSerializer(serializers.ModelSerializer):
    total_users = serializers.SerializerMethodField()

    class Meta:
        model = UserGroup
        fields = ['id', 'name', 'code', 'description', 'status',
                  'total_users', 'created_at']

    def get_total_users(self, obj):
        return obj.user_memberships.count()


class UserGroupMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserGroupMembership
        fields = ['id', 'user_id', 'user_name', 'user_email', 'added_at']


class UserGroupDetailSerializer(serializers.ModelSerializer):
    total_users = serializers.SerializerMethodField()
    screen_permissions = ScreenPermissionSerializer(many=True, read_only=True)
    members = serializers.SerializerMethodField()

    class Meta:
        model = UserGroup
        fields = ['id', 'name', 'code', 'description', 'status',
                  'total_users', 'screen_permissions', 'members',
                  'created_at', 'updated_at']

    def get_total_users(self, obj):
        return obj.user_memberships.count()

    def get_members(self, obj):
        qs = obj.user_memberships.select_related('user').all()
        return UserGroupMemberSerializer(qs, many=True).data


class UserGroupWriteSerializer(serializers.ModelSerializer):
    screen_permissions = ScreenPermissionWriteSerializer(many=True, required=False)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True,
    )

    class Meta:
        model = UserGroup
        fields = ['name', 'code', 'description', 'status',
                  'screen_permissions', 'member_ids']

    def create(self, validated_data):
        perms_data = validated_data.pop('screen_permissions', [])
        member_ids = validated_data.pop('member_ids', [])
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user
        group = UserGroup.objects.create(**validated_data)
        self._sync_permissions(group, perms_data)
        self._sync_members(group, member_ids, request)
        return group

    def update(self, instance, validated_data):
        perms_data = validated_data.pop('screen_permissions', None)
        member_ids = validated_data.pop('member_ids', None)
        request = self.context.get('request')
        if request and request.user:
            validated_data['updated_by'] = request.user
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if perms_data is not None:
            self._sync_permissions(instance, perms_data)
        if member_ids is not None:
            self._sync_members(instance, member_ids, request)
        return instance

    @staticmethod
    def _sync_permissions(group, perms_data):
        group.screen_permissions.all().delete()
        for perm in perms_data:
            ScreenPermission.objects.create(group=group, **perm)

    @staticmethod
    def _sync_members(group, member_ids, request):
        group.user_memberships.all().delete()
        added_by = request.user if request and request.user else None
        for uid in member_ids:
            UserGroupMembership.objects.create(
                group=group,
                user_id=uid,
                added_by=added_by,
            )


# ── UserScreenOverride ────────────────────────────────────────────────────────
class UserScreenOverrideSerializer(serializers.ModelSerializer):
    screen_code = serializers.CharField(source='screen.code', read_only=True)
    screen_name = serializers.CharField(source='screen.name', read_only=True)

    class Meta:
        model = UserScreenOverride
        fields = [
            'id', 'user', 'screen', 'screen_code', 'screen_name',
            'can_view', 'can_add', 'can_edit', 'can_delete',
            'can_approve', 'can_reject', 'can_export', 'can_print',
        ]


# ── User ──────────────────────────────────────────────────────────────────────
class UserListSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(read_only=True)
    group_names = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'role_name',
                  'group', 'group_names', 'employee_id', 'gender',
                  'status', 'homepage', 'is_active', 'created_at']

    def get_group_names(self, obj):
        names = list(obj.groups_m2m.values_list('name', flat=True))
        if obj.group and obj.group.name not in names:
            names.insert(0, obj.group.name)
        return names


class UserDetailSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(read_only=True)
    group_name = serializers.SerializerMethodField()
    group_ids = serializers.SerializerMethodField()
    group_names = serializers.SerializerMethodField()
    screen_overrides = UserScreenOverrideSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'role_name',
                  'group', 'group_name', 'group_ids', 'group_names',
                  'employee_id', 'gender', 'status', 'homepage',
                  'is_active', 'is_staff',
                  'profile_picture', 'screen_overrides',
                  'created_at', 'updated_at']

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None

    def get_group_ids(self, obj):
        ids = list(obj.groups_m2m.values_list('id', flat=True))
        if obj.group_id and obj.group_id not in ids:
            ids.insert(0, obj.group_id)
        return ids

    def get_group_names(self, obj):
        names = list(obj.groups_m2m.values_list('name', flat=True))
        if obj.group and obj.group.name not in names:
            names.insert(0, obj.group.name)
        return names


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    group_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True,
    )

    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'password', 'confirm_password',
                  'role', 'group', 'group_ids', 'employee_id', 'gender',
                  'status', 'homepage', 'is_active']

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        group_ids = validated_data.pop('group_ids', [])
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if group_ids:
            for gid in group_ids:
                UserGroupMembership.objects.get_or_create(user=user, group_id=gid)
        elif user.group_id:
            UserGroupMembership.objects.get_or_create(user=user, group_id=user.group_id)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    group_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True,
    )

    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'role', 'group', 'group_ids',
                  'employee_id', 'gender', 'status', 'homepage', 'is_active']

    def update(self, instance, validated_data):
        group_ids = validated_data.pop('group_ids', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if group_ids is not None:
            instance.group_memberships.all().delete()
            for gid in group_ids:
                UserGroupMembership.objects.get_or_create(user=instance, group_id=gid)
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data


# ── Effective permissions (read-only, for /users/me/permissions/) ─────────────
class EffectivePermissionSerializer(serializers.Serializer):
    screen_code = serializers.CharField()
    screen_name = serializers.CharField()
    can_view = serializers.BooleanField()
    can_add = serializers.BooleanField()
    can_edit = serializers.BooleanField()
    can_delete = serializers.BooleanField()
    can_approve = serializers.BooleanField()
    can_reject = serializers.BooleanField()
    can_export = serializers.BooleanField()
    can_print = serializers.BooleanField()
