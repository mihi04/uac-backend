"""
apps/authentication/urls.py
"""

from django.urls import path
from .views import LoginView, LogoutView, CustomTokenRefreshView, MeView

urlpatterns = [
    path('login/',   LoginView.as_view(),              name='auth-login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/',  LogoutView.as_view(),              name='auth-logout'),
    path('me/',      MeView.as_view(),                  name='auth-me'),
]
