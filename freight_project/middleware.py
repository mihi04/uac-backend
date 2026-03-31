"""
freight_project/middleware.py
Audit log + request logging middleware.
"""

import time
import logging
import json

logger = logging.getLogger('apps')


class RequestLoggingMiddleware:
    """Logs every incoming request with method, path, status code, and duration."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = round((time.time() - start) * 1000, 2)

        user = getattr(request, 'user', None)
        user_info = f"user={user.id}" if user and user.is_authenticated else "anonymous"
        logger.info(
            f"{request.method} {request.path} → {response.status_code} "
            f"[{duration}ms] {user_info}"
        )
        return response


class AuditLogMiddleware:
    """
    Captures write operations (POST/PUT/PATCH/DELETE) and stores them
    in the audit_logs table after the response is sent.
    Skips auth endpoints to avoid logging credentials.
    """

    SKIP_PATHS = ['/api/v1/auth/login', '/api/v1/auth/refresh', '/admin/']
    WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.method in self.WRITE_METHODS
            and response.status_code < 400
            and not any(request.path.startswith(p) for p in self.SKIP_PATHS)
        ):
            self._log_audit(request, response)

        return response

    def _log_audit(self, request, response):
        try:
            from apps.users.models import AuditLog  # late import avoids circular deps
            user = getattr(request, 'user', None)

            AuditLog.objects.create(
                table_name=self._extract_table(request.path),
                action=request.method,
                changed_by=user if (user and user.is_authenticated) else None,
                ip_address=self._get_ip(request),
                endpoint=request.path,
            )
        except Exception:
            pass  # Never let audit logging break a real request

    @staticmethod
    def _extract_table(path: str) -> str:
        """Best-effort: derive resource name from URL path."""
        parts = [p for p in path.strip('/').split('/') if p and not p.isdigit()]
        return parts[-1] if parts else 'unknown'

    @staticmethod
    def _get_ip(request) -> str:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')
