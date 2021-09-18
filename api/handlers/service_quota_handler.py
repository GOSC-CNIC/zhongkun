from core import errors as exceptions
from service.managers import ServicePrivateQuotaManager, ServiceShareQuotaManager
from api.viewsets import CustomGenericViewSet
from api import serializers


class ServiceQuotaHandler:
    @staticmethod
    def list_privete_quotas(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        try:
            servers = ServicePrivateQuotaManager().get_privete_queryset(service_id=service_id)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(servers, request, view=view)
            serializer = serializers.VmServicePrivateQuotaSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def list_share_quotas(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        try:
            servers = ServiceShareQuotaManager().get_share_queryset(service_id=service_id)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(servers, request, view=view)
            serializer = serializers.VmServiceShareQuotaSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))
