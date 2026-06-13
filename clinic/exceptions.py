"""Exception handling for API requests."""

import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """Log API errors while preserving DRF's default error responses."""

    response = exception_handler(exc, context)
    request = context.get("request")
    view = context.get("view")
    method = getattr(request, "method", "")
    path = getattr(request, "path", "")
    user = getattr(request, "user", None)
    username = getattr(user, "username", "")
    view_name = view.__class__.__name__ if view else ""
    error_type = exc.__class__.__name__

    if response is None:
        logger.exception(
            "api_error status_code=500 method=%s path=%s view=%s user=%s "
            "error_type=%s",
            method,
            path,
            view_name,
            username,
            error_type,
        )
        return response

    logger.warning(
        "api_error status_code=%s method=%s path=%s view=%s user=%s error_type=%s",
        response.status_code,
        method,
        path,
        view_name,
        username,
        error_type,
    )
    return response
