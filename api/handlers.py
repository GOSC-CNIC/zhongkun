from django.utils.translation import gettext as _
from rest_framework.response import Response

from servers.models import Server
from service.managers import UserQuotaManager
from . import serializers
from . import exceptions


class UserQuotaHandler:
    @staticmethod
    def list_quotas(view, request, kwargs):
        service_id = request.query_params.get('service', None)
        usable = request.query_params.get('usable', '').lower()
        usable = True if usable == 'true' else False

        try:
            queryset = UserQuotaManager().filter_quota_queryset(user=request.user, service=service_id, usable=usable)
            paginator = view.paginator
            quotas = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.UserQuotaSerializer(quotas, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

        return response

    @staticmethod
    def list_quota_servers(view, request, kwargs):
        quota_id = kwargs.get(view.lookup_field)
        quota = UserQuotaManager().get_quota_by_id(quota_id)
        if not quota:
            return view.exception_reponse(
                exceptions.NotFound(message='资源配额不存在'))

        if quota.user_id != request.user.id:
            return view.exception_reponse(
                exceptions.AccessDenied(message=_('无权访问此资源配额')))

        try:
            queryset = Server.objects.filter(user_quota=quota)
            paginator = view.pagination_class()
            servers = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ServerSimpleSerializer(servers, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)
