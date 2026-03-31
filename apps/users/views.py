"""
apps/users/views.py
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import (
    User, Role, UserGroup, Screen,
    ScreenPermission, UserScreenOverride, UserGroupMembership,
)
from .serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, ChangePasswordSerializer,
    RoleSerializer,
    UserGroupListSerializer, UserGroupDetailSerializer, UserGroupWriteSerializer,
    ScreenSerializer, ScreenPermissionSerializer,
    UserScreenOverrideSerializer, EffectivePermissionSerializer,
)
from .permissions import IsAdminOrManager


# ── Users ─────────────────────────────────────────────────────────────────────
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('role', 'group').prefetch_related('groups_m2m').all()
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    search_fields = ['name', 'email', 'employee_id']
    filterset_fields = ['is_active', 'status', 'group']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        if self.action == 'retrieve':
            return UserDetailSerializer
        return UserListSerializer

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.status = 'inactive'
        user.save()
        return Response({'detail': 'User deactivated.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Incorrect password.'},
                            status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Password updated successfully.'})

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='me/permissions')
    def my_permissions(self, request):
        """Return effective merged permissions for every active screen."""
        screens = Screen.objects.filter(is_active=True)
        result = []
        for scr in screens:
            perms = request.user.get_effective_permissions(scr.code)
            perms['screen_code'] = scr.code
            perms['screen_name'] = scr.name
            result.append(perms)
        serializer = EffectivePermissionSerializer(result, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='overrides')
    def overrides(self, request, pk=None):
        user = self.get_object()
        if request.method == 'GET':
            qs = user.screen_overrides.select_related('screen').all()
            return Response(UserScreenOverrideSerializer(qs, many=True).data)
        serializer = UserScreenOverrideSerializer(data={**request.data, 'user': user.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='permissions')
    def user_permissions(self, request, pk=None):
        user = self.get_object()
        screens = Screen.objects.filter(is_active=True)
        result = []
        for scr in screens:
            perms = user.get_effective_permissions(scr.code)
            perms['screen_code'] = scr.code
            perms['screen_name'] = scr.name
            result.append(perms)
        return Response(EffectivePermissionSerializer(result, many=True).data)


# ── Roles ─────────────────────────────────────────────────────────────────────
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


# ── User Groups ───────────────────────────────────────────────────────────────
class UserGroupViewSet(viewsets.ModelViewSet):
    queryset = UserGroup.objects.prefetch_related(
        'screen_permissions', 'screen_permissions__screen',
        'user_memberships', 'user_memberships__user',
    ).all()
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    search_fields = ['name', 'code', 'description']
    filterset_fields = ['status']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return UserGroupWriteSerializer
        if self.action == 'retrieve':
            return UserGroupDetailSerializer
        return UserGroupListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    @action(detail=True, methods=['post'], url_path='clone')
    def clone(self, request, pk=None):
        """Clone group permissions into a new group."""
        source = self.get_object()
        new_name = request.data.get('name', f'{source.name} (Copy)')
        new_code = request.data.get('code', f'{source.code}_COPY' if source.code else '')
        new_group = UserGroup.objects.create(
            name=new_name,
            code=new_code,
            description=source.description,
            status=True,
            created_by=request.user,
            updated_by=request.user,
        )
        for sp in source.screen_permissions.all():
            ScreenPermission.objects.create(
                group=new_group,
                screen=sp.screen,
                can_view=sp.can_view,
                can_add=sp.can_add,
                can_edit=sp.can_edit,
                can_delete=sp.can_delete,
                can_approve=sp.can_approve,
                can_reject=sp.can_reject,
                can_export=sp.can_export,
                can_print=sp.can_print,
            )
        return Response(
            UserGroupDetailSerializer(new_group).data,
            status=status.HTTP_201_CREATED,
        )


# ── Screens ───────────────────────────────────────────────────────────────────
class ScreenViewSet(viewsets.ModelViewSet):
    queryset = Screen.objects.filter(is_active=True)
    serializer_class = ScreenSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['ordering', 'name']
