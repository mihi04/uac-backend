"""
apps/users/models.py
Custom User model + Role, UserGroup, Screen-level RBAC, AuditLog.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from freight_project.base_model import TimeStampedModel


# ── Role ──────────────────────────────────────────────────────────────────────
class Role(models.Model):
    """Defines what a user can do (admin, manager, sales, accounts, viewer …)."""

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, help_text="Fine-grained permission flags")

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'roles'
        ordering = ['name']


# ── UserGroup ─────────────────────────────────────────────────────────────────
class UserGroup(models.Model):
    """Logical team grouping — e.g. Sales Team, Operations, Finance."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=40, unique=True, blank=True, null=True,
                            help_text='Short code e.g. SALES, ACCT')
    description = models.TextField(blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+',
    )
    updated_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+',
    )

    def __str__(self):
        return self.name

    @property
    def total_users(self):
        return self.memberships.count()

    class Meta:
        db_table = 'user_groups'
        ordering = ['name']


# ── Screen Registry ───────────────────────────────────────────────────────────
class Screen(models.Model):
    """Every navigable screen/module in the application."""

    code = models.CharField(max_length=60, unique=True,
                            help_text='Frontend route key, e.g. dashboard, quotation')
    name = models.CharField(max_length=120,
                            help_text='Human-readable label shown in permission matrix')
    module = models.CharField(max_length=60, blank=True,
                              help_text='Logical grouping: core, admin, finance …')
    ordering = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'screens'
        ordering = ['ordering', 'name']


# ── Screen Permission (group → screen → action flags) ────────────────────────
class ScreenPermission(models.Model):
    """Which actions a given UserGroup may perform on a given Screen."""

    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE,
                              related_name='screen_permissions')
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE,
                               related_name='group_permissions')
    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_reject = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    can_print = models.BooleanField(default=False)

    class Meta:
        db_table = 'screen_permissions'
        unique_together = [('group', 'screen')]
        ordering = ['group', 'screen']

    def __str__(self):
        return f"{self.group.name} → {self.screen.name}"


# ── User-level screen override ────────────────────────────────────────────────
class UserScreenOverride(models.Model):
    """
    Per-user permission override that adds or removes access beyond what
    their group(s) provide.  `grant=True` means ADD access, `grant=False`
    means explicitly DENY even if group allows it.
    """

    user = models.ForeignKey('users.User', on_delete=models.CASCADE,
                             related_name='screen_overrides')
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE,
                               related_name='user_overrides')
    can_view = models.BooleanField(null=True, blank=True)
    can_add = models.BooleanField(null=True, blank=True)
    can_edit = models.BooleanField(null=True, blank=True)
    can_delete = models.BooleanField(null=True, blank=True)
    can_approve = models.BooleanField(null=True, blank=True)
    can_reject = models.BooleanField(null=True, blank=True)
    can_export = models.BooleanField(null=True, blank=True)
    can_print = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'user_screen_overrides'
        unique_together = [('user', 'screen')]

    def __str__(self):
        return f"Override: {self.user} → {self.screen.name}"


# ── Custom User Manager ────────────────────────────────────────────────────────
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


# ── User ──────────────────────────────────────────────────────────────────────
class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Central user model.  Email is the unique login identifier.
    """

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    class UserStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        SUSPENDED = 'suspended', 'Suspended'

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='users')
    # Legacy single-group FK kept for backward-compat; prefer M2M `groups_m2m`.
    group = models.ForeignKey(UserGroup, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='legacy_users')
    groups_m2m = models.ManyToManyField(UserGroup, blank=True,
                                        related_name='memberships',
                                        through='UserGroupMembership',
                                        through_fields=('user', 'group'))
    employee_id = models.CharField(max_length=30, blank=True, unique=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    status = models.CharField(max_length=15, choices=UserStatus.choices,
                              default=UserStatus.ACTIVE, db_index=True)
    homepage = models.CharField(max_length=60, blank=True, default='dashboard',
                                help_text='Default landing screen code')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='users/profiles/', blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def role_name(self):
        return self.role.name if self.role else None

    def get_effective_permissions(self, screen_code):
        """
        Merge group-level + user-override permissions for a screen.
        Returns dict of action→bool.  Default deny.
        """
        actions = ['can_view', 'can_add', 'can_edit', 'can_delete',
                   'can_approve', 'can_reject', 'can_export', 'can_print']
        merged = {a: False for a in actions}

        group_ids = list(self.groups_m2m.values_list('id', flat=True))
        if self.group_id and self.group_id not in group_ids:
            group_ids.append(self.group_id)

        perms = ScreenPermission.objects.filter(
            group_id__in=group_ids,
            screen__code=screen_code,
        )
        for p in perms:
            for a in actions:
                if getattr(p, a, False):
                    merged[a] = True

        try:
            ovr = UserScreenOverride.objects.get(user=self, screen__code=screen_code)
            for a in actions:
                val = getattr(ovr, a, None)
                if val is True:
                    merged[a] = True
                elif val is False:
                    merged[a] = False
        except UserScreenOverride.DoesNotExist:
            pass

        return merged

    class Meta:
        db_table = 'users'
        ordering = ['name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]


# ── M2M through table ────────────────────────────────────────────────────────
class UserGroupMembership(models.Model):
    """Explicit M2M so we can track who added the user and when."""

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='group_memberships')
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE,
                              related_name='user_memberships')
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'user_group_memberships'
        unique_together = [('user', 'group')]

    def __str__(self):
        return f"{self.user.name} ∈ {self.group.name}"


# ── AuditLog ──────────────────────────────────────────────────────────────────
class AuditLog(models.Model):
    """Immutable record of every write operation."""

    table_name = models.CharField(max_length=80)
    record_id = models.BigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=20)
    endpoint = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    payload_snapshot = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} {self.table_name} @ {self.changed_at}"

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['table_name', 'record_id']),
            models.Index(fields=['changed_by']),
            models.Index(fields=['changed_at']),
        ]
