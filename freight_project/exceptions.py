"""
freight_project/exceptions.py — Uniform error envelope for all API errors.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('apps')


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'status': 'error',
            'code': response.status_code,
            'errors': response.data,
        }
        logger.warning(
            f"API error {response.status_code}: {response.data} "
            f"| view={context.get('view').__class__.__name__}"
        )
        return Response(error_data, status=response.status_code)

    # Unhandled exceptions → 500
    logger.exception(f"Unhandled exception in {context.get('view')}", exc_info=exc)
    return Response(
        {'status': 'error', 'code': 500, 'errors': 'Internal server error.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
