"""
apps/users/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RoleViewSet, UserGroupViewSet, ScreenViewSet

router = DefaultRouter()
router.register('roles', RoleViewSet, basename='roles')
router.register('groups', UserGroupViewSet, basename='user-groups')
router.register('screens', ScreenViewSet, basename='screens')
router.register('', UserViewSet, basename='users')

urlpatterns = [path('', include(router.urls))]
