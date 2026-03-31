# Seed: application screens, default user groups, and baseline permission matrix.

from django.db import migrations

SCREENS = [
    ('dashboard',       'Dashboard',              'core',    1),
    ('business-reg',    'Business Registration',   'core',    2),
    ('customer-reg',    'Customer Registration',   'core',    3),
    ('quotation',       'Quotation',               'core',    4),
    ('invoice',         'Billing / Invoice',       'finance', 5),
    ('pricing',         'Pricing',                 'finance', 6),
    ('delinquency',     'Delinquency',             'finance', 7),
    ('accounting',      'Accounting',              'finance', 8),
    ('reports',         'Reports',                 'core',    9),
    ('users-search',    'Users',                   'admin',  10),
    ('users-add',       'Users – Add',             'admin',  11),
    ('usergroup-search','User Group',              'admin',  12),
    ('usergroup-add',   'User Group – Add',        'admin',  13),
    ('admin',           'Admin Settings',          'admin',  14),
]

GROUPS = [
    {
        'name': 'Super Admin',
        'code': 'SUPER_ADMIN',
        'description': 'Full access to all screens and settings',
        'all_access': True,
    },
    {
        'name': 'Admin',
        'code': 'ADMIN',
        'description': 'Manage users, groups, and system configuration',
        'screens': {
            'dashboard': 'v',
            'users-search': 'vaed',
            'users-add': 'vaed',
            'usergroup-search': 'vaed',
            'usergroup-add': 'vaed',
            'admin': 'vaed',
            'reports': 'vx',
        },
    },
    {
        'name': 'Sales & Marketing',
        'code': 'SALES',
        'description': 'Quotations, leads, customer records, own reports',
        'screens': {
            'dashboard': 'v',
            'business-reg': 'vae',
            'customer-reg': 'vae',
            'quotation': 'vaed',
            'reports': 'vx',
        },
    },
    {
        'name': 'Sales Manager',
        'code': 'SALES_MGR',
        'description': 'Sales access + approvals + team reports',
        'screens': {
            'dashboard': 'v',
            'business-reg': 'vae',
            'customer-reg': 'vae',
            'quotation': 'vaedp',
            'reports': 'vxp',
        },
    },
    {
        'name': 'Accountant',
        'code': 'ACCT',
        'description': 'Billing, invoices, payments, finance reports',
        'screens': {
            'dashboard': 'v',
            'invoice': 'vaed',
            'pricing': 'vae',
            'delinquency': 'v',
            'accounting': 'vaed',
            'reports': 'vx',
        },
    },
    {
        'name': 'Accounts Manager',
        'code': 'ACCT_MGR',
        'description': 'Accounts access + approvals + correction rights',
        'screens': {
            'dashboard': 'v',
            'invoice': 'vaedp',
            'pricing': 'vaed',
            'delinquency': 'vaed',
            'accounting': 'vaedp',
            'reports': 'vxp',
        },
    },
    {
        'name': 'Operations',
        'code': 'OPS',
        'description': 'Order processing, task management, workflow',
        'screens': {
            'dashboard': 'v',
            'business-reg': 'v',
            'customer-reg': 'v',
            'quotation': 'v',
            'invoice': 'v',
            'reports': 'v',
        },
    },
    {
        'name': 'Support',
        'code': 'SUPPORT',
        'description': 'Ticketing, customer support, knowledge base',
        'screens': {
            'dashboard': 'v',
            'customer-reg': 'v',
            'reports': 'v',
        },
    },
    {
        'name': 'HR',
        'code': 'HR',
        'description': 'Employee records, onboarding, access requests',
        'screens': {
            'dashboard': 'v',
            'users-search': 'v',
            'reports': 'v',
        },
    },
    {
        'name': 'Auditor / Read Only',
        'code': 'AUDITOR',
        'description': 'View-only access to selected screens',
        'screens': {
            'dashboard': 'v',
            'quotation': 'v',
            'invoice': 'v',
            'accounting': 'v',
            'reports': 'vx',
            'users-search': 'v',
            'usergroup-search': 'v',
        },
    },
]

FLAG_MAP = {
    'v': 'can_view',
    'a': 'can_add',
    'e': 'can_edit',
    'd': 'can_delete',
    'p': 'can_approve',
    'r': 'can_reject',
    'x': 'can_export',
    't': 'can_print',
}

ALL_ACTIONS = list(FLAG_MAP.values())


def forwards(apps, schema_editor):
    Screen = apps.get_model('users', 'Screen')
    UserGroup = apps.get_model('users', 'UserGroup')
    ScreenPermission = apps.get_model('users', 'ScreenPermission')

    screen_map = {}
    for code, name, module, ordering in SCREENS:
        obj, _ = Screen.objects.get_or_create(
            code=code,
            defaults={'name': name, 'module': module, 'ordering': ordering, 'is_active': True},
        )
        screen_map[code] = obj

    for gdef in GROUPS:
        grp, _ = UserGroup.objects.get_or_create(
            name=gdef['name'],
            defaults={
                'code': gdef.get('code', ''),
                'description': gdef.get('description', ''),
                'status': True,
            },
        )
        if not grp.code and gdef.get('code'):
            grp.code = gdef['code']
            grp.description = gdef.get('description', grp.description)
            grp.save()

        if gdef.get('all_access'):
            for scr in screen_map.values():
                ScreenPermission.objects.get_or_create(
                    group=grp, screen=scr,
                    defaults={a: True for a in ALL_ACTIONS},
                )
        else:
            for scode, flags in (gdef.get('screens') or {}).items():
                scr = screen_map.get(scode)
                if not scr:
                    continue
                perm_kw = {a: False for a in ALL_ACTIONS}
                for ch in flags:
                    field = FLAG_MAP.get(ch)
                    if field:
                        perm_kw[field] = True
                ScreenPermission.objects.get_or_create(
                    group=grp, screen=scr,
                    defaults=perm_kw,
                )


def backwards(apps, schema_editor):
    Screen = apps.get_model('users', 'Screen')
    ScreenPermission = apps.get_model('users', 'ScreenPermission')
    ScreenPermission.objects.all().delete()
    Screen.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_rbac_screen_permissions'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
