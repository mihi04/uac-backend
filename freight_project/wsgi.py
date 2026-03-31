"""
freight_project/wsgi.py — WSGI config for production (gunicorn / uWSGI).
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freight_project.settings')
application = get_wsgi_application()
