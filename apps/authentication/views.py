"""
apps/authentication/views.py
JWT login / refresh / logout + token introspection.
"""

import logging
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import LoginSerializer, TokenResponseSerializer

User = get_user_model()
logger = logging.getLogger('apps')


class LoginView(APIView):
    """
    POST /api/v1/auth/login
    Body: { "email": "...", "password": "..." }
    Returns: access_token, refresh_token, user profile.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        # Track last login IP
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        user.last_login_ip = ip.split(',')[0].strip() if ip else None
        user.save(update_fields=['last_login_ip'])

        logger.info(f"Login success: {user.email} from {ip}")

        return Response({
            'status': 'success',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'token_type': 'Bearer',
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role_name,
                'is_staff': user.is_staff,
            },
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout
    Blacklists the refresh token so it cannot be reused.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'detail': 'refresh_token is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            raise InvalidToken(str(e))

        logger.info(f"Logout: {request.user.email}")
        return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/v1/auth/refresh
    Standard simplejwt refresh — wrapped with uniform response envelope.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response({
                'status': 'success',
                'access_token': response.data['access'],
                'refresh_token': response.data.get('refresh', ''),
            })
        return response


class MeView(APIView):
    """GET /api/v1/auth/me  — Returns the currently authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role_name,
            'group': user.group.name if user.group else None,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        })
