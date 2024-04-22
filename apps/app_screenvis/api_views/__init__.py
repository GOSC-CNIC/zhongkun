from django.http import Http404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import set_rollback
from rest_framework.exceptions import (APIException, PermissionDenied, NotAuthenticated, AuthenticationFailed)

from apps.app_screenvis.utils import errors


def exception_handler(exc, context):
    if isinstance(exc, errors.Error):
        pass
    elif isinstance(exc, Http404):
        exc = errors.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = errors.AccessDenied(message=str(exc))
    elif isinstance(exc, AuthenticationFailed):
        exc = errors.AuthenticationFailed(message=str(exc))
    elif isinstance(exc, NotAuthenticated):
        exc = errors.NotAuthenticated(message=str(exc))
    elif isinstance(exc, APIException):
        if isinstance(exc.detail, (list, dict)):
            data = exc.detail
        else:
            data = {'detail': exc.detail}

        exc = errors.Error(message=str(data), status_code=exc.status_code, code=exc.default_code)
    else:
        exc = errors.convert_to_error(exc)

    set_rollback()
    return Response(exc.err_data(), status=exc.status_code)


class NormalGenericViewSet(viewsets.GenericViewSet):
    from django.db.models import QuerySet
    queryset = QuerySet().none()

    @staticmethod
    def exception_response(exc):
        if not isinstance(exc, errors.Error):
            exc = errors.Error(message=str(exc))

        return Response(data=exc.err_data(), status=exc.status_code)

    def get_exception_handler(self):
        return exception_handler
