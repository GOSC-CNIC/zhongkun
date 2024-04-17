from rest_framework import viewsets
from rest_framework.response import Response

from apps.app_screenvis.utils import errors


class NormalGenericViewSet(viewsets.GenericViewSet):
    from django.db.models import QuerySet
    queryset = QuerySet().none()

    @staticmethod
    def exception_response(exc):
        if not isinstance(exc, errors.Error):
            exc = errors.Error(message=str(exc))

        return Response(data=exc.err_data(), status=exc.status_code)
