"""
freight_project/asgi.py — ASGI config (Daphne / uvicorn for WebSocket support).
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freight_project.settings')
application = get_asgi_application()
