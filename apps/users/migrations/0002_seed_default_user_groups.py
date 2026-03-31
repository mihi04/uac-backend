# Generated manually — seed user groups shown in Smart Revenue Management UI

from django.db import migrations


def seed_user_groups(apps, schema_editor):
    UserGroup = apps.get_model("users", "UserGroup")
    defaults = [
        ("Sales & Marketing", "Sales and marketing team"),
        ("Accountant", "Accounting and finance team"),
    ]
    for name, description in defaults:
        UserGroup.objects.get_or_create(
            name=name,
            defaults={"description": description, "status": True},
        )


def unseed_user_groups(apps, schema_editor):
    UserGroup = apps.get_model("users", "UserGroup")
    UserGroup.objects.filter(name__in=["Sales & Marketing", "Accountant"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_user_groups, unseed_user_groups),
    ]
