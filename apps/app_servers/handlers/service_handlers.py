from django.utils.translation import gettext as _
from rest_framework.response import Response

from apps.app_servers.managers import (
    ServicePrivateQuotaManager, ServiceShareQuotaManager, ServiceManager
)
from apps.app_servers.models import ServiceConfig
from apps.app_servers import serializers
from core import errors as exceptions
from apps.api.viewsets import serializer_error_msg, CustomGenericViewSet


class VmServiceHandler:
    @staticmethod
    def get_user_perm_service(_id, user):
        """
        :raises: Error
        """
        service = ServiceManager.get_service_by_id(_id)
        if service is None:
            raise exceptions.ServiceNotExist()

        if not ServiceManager.has_perm(user_id=user.id, service_id=_id):
            raise exceptions.AccessDenied(message=_('你没有此服务的管理权限'))

        return service

    @staticmethod
    def get_private_quota(view, request, kwargs):
        """
        查询服务私有配额
        """
        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            quota = ServicePrivateQuotaManager().get_quota(service=service)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServicePrivateQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def change_private_quota(view, request, kwargs):
        """
        修改服务私有配额
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        data = serializer.validated_data
        private_ip_total = data.get('private_ip_total')
        public_ip_total = data.get('public_ip_total')
        vcpu_total = data.get('vcpu_total')
        ram_total = data.get('ram_total')
        disk_size_total = data.get('disk_size_total')

        try:
            quota = ServicePrivateQuotaManager().update(
                service=service, vcpus=vcpu_total, ram_gib=ram_total, disk_size=disk_size_total,
                public_ip=public_ip_total, private_ip=private_ip_total, only_increase=True)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServicePrivateQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def get_share_quota(view, request, kwargs):
        """
        查询服务共享配额
        """
        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            quota = ServiceShareQuotaManager().get_quota(service=service)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServiceShareQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def change_share_quota(view, request, kwargs):
        """
        修改服务共享配额
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        data = serializer.validated_data
        private_ip_total = data.get('private_ip_total')
        public_ip_total = data.get('public_ip_total')
        vcpu_total = data.get('vcpu_total')
        ram_total = data.get('ram_total')
        disk_size_total = data.get('disk_size_total')

        try:
            quota = ServiceShareQuotaManager().update(
                service=service, vcpus=vcpu_total, ram_gib=ram_total, disk_size=disk_size_total,
                public_ip=public_ip_total, private_ip=private_ip_total, only_increase=True)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServiceShareQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def list_services(view, request, kwargs):
        """
        list接入服务provider
        """
        org_id = request.query_params.get('org_id', None)
        center_id = request.query_params.get('center_id', None)
        status = request.query_params.get('status', None)
        with_admin_users = request.query_params.get('with_admin_users', None)
        with_admin_users = with_admin_users is not None

        if status is not None:
            if status not in ServiceConfig.Status.values:
                return view.exception_response(
                    exceptions.InvalidArgument(message=_('服务单元服务状态查询参数值无效'), code='InvalidStatus')
                )

        if view.is_as_admin_request(request):
            service_qs = ServiceManager.admin_list_service_queryset(
                admin_user=request.user, org_id=org_id, center_id=center_id, status=status)
        else:
            with_admin_users = False
            service_qs = ServiceManager().filter_service(org_id=org_id, center_id=center_id, status=status)

        return view.paginate_service_response(request=request, qs=service_qs, with_admin_users=with_admin_users)


class ServiceQuotaHandler:
    @staticmethod
    def list_privete_quotas(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        data_center_id = request.query_params.get('data_center_id', None)
        try:
            qs = ServicePrivateQuotaManager().get_privete_queryset(
                center_id=data_center_id, service_id=service_id)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(qs, request, view=view)
            serializer = serializers.VmServicePrivateQuotaSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def list_share_quotas(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        data_center_id = request.query_params.get('data_center_id', None)
        try:
            qs = ServiceShareQuotaManager().get_share_queryset(
                center_id=data_center_id, service_id=service_id)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(qs, request, view=view)
            serializer = serializers.VmServiceShareQuotaSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))
