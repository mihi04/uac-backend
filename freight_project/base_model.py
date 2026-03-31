"""
freight_project/base_model.py
Abstract base model — every table inherits audit fields from here.
"""

from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    """Adds created_at / updated_at to every model."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditedModel(TimeStampedModel):
    """Adds created_by / updated_by on top of timestamps."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    class Meta:
        abstract = True

    def save_with_user(self, user, *args, **kwargs):
        if not self.pk:
            self.created_by = user
        self.updated_by = user
        self.save(*args, **kwargs)
