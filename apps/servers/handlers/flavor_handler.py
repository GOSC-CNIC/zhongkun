from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors as exceptions
from apps.servers.managers import ServiceManager
from apps.servers.models import Flavor
from apps.servers.managers import FlavorManager
from apps.servers import serializers as server_serializers
from apps.api.viewsets import CustomGenericViewSet, serializer_error_msg


def str_to_true_false(val: str):
    if not isinstance(val, str):
        return val

    if val.lower() == 'true':
        return True
    elif val.lower() == 'false':
        return False
    else:
        raise exceptions.InvalidArgument(
            message=_('值无效，必须为true或者false'))


class FlavorHandler:
    @staticmethod
    def list_flavors(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        try:
            flavors = Flavor.objects.filter(service_id=service_id, enable=True).order_by('vcpus', 'ram').all()
            serializer = server_serializers.FlavorSerializer(flavors, many=True)
        except Exception as exc:
            return view.exception_response(
                exceptions.APIException(message=str(exc)))

        return Response(data={"flavors": serializer.data})

    @staticmethod
    def admin_list_flavors(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        enable = request.query_params.get('enable', None)

        try:
            enable = str_to_true_false(enable)
            qs = FlavorManager().get_admin_flavor_queryset(
                user=request.user, service_id=service_id, enable=enable
            )
            flavors = view.paginate_queryset(queryset=qs)
            serializer = server_serializers.FlavorSerializer(flavors, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def admin_create_flavor(view: CustomGenericViewSet, request, kwargs):
        try:
            params = FlavorHandler._flavor_create_validate_params(view=view, request=request)
            service_id = params['service_id']
            service = ServiceManager.get_service(service_id=service_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        vcpus = params['vcpus']
        ram = params['ram']
        enable = params['enable']
        user = request.user

        if not (user.is_federal_admin() or service.user_has_perm(user)):
            return view.exception_response(
                exceptions.AccessDenied(message=_('你没有服务单元的管理权限'))
            )

        try:
            flavor = Flavor(vcpus=vcpus, ram=ram, service_id=service_id, disk=0, flavor_id='', enable=enable)
            flavor.save(force_insert=True)
        except Exception as exc:
            return view.exception_response(
                exceptions.APIException(message=_('创建配置样式时错误。') + str(exc))
            )

        return Response(data=server_serializers.FlavorSerializer(flavor).data)

    @staticmethod
    def _flavor_create_validate_params(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            exc = exceptions.BadRequest(message=msg)
            raise exc

        data = serializer.validated_data
        vcpus = data['vcpus']
        ram = data['ram']

        if not (1 <= vcpus <= 256):
            raise exceptions.InvalidArgument(message=_('cpu数可取值在1-256之间'), code='InvalidCPUs')

        if not (1 <= ram <= 1024):
            raise exceptions.InvalidArgument(message=_('内存大小必须在1-1024之间'), code='InvalidRam')

        return data

    @staticmethod
    def admin_update_flavor(view: CustomGenericViewSet, request, kwargs):
        flavor_id = kwargs[view.lookup_field]
        user = request.user

        try:
            params = FlavorHandler._flavor_create_validate_params(view=view, request=request)
            flavor = Flavor.objects.filter(id=flavor_id).first()
            if flavor is None:
                raise exceptions.TargetNotExist(message=_('配置样式不存在'))

            old_service = flavor.service
            if not user.is_federal_admin():
                if not (old_service and old_service.user_has_perm(user)):
                    raise exceptions.AccessDenied(message=_('你没有此配置样式的管理权限'))

            service_id = params['service_id']
            new_service = ServiceManager.get_service(service_id=service_id)
            if not user.is_federal_admin():
                if not new_service.user_has_perm(user):
                    raise exceptions.AccessDenied(message=_('你没有指定服务单元的管理权限'))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            flavor.vcpus = params['vcpus']
            flavor.ram = params['ram']
            flavor.enable = params['enable']
            flavor.service_id = new_service.id
            flavor.save(update_fields=['vcpus', 'ram', 'enable', 'service_id'])
        except Exception as exc:
            return view.exception_response(
                exceptions.APIException(message=_('更新配置样式时错误。') + str(exc))
            )

        return Response(data=server_serializers.FlavorSerializer(flavor).data)

    @staticmethod
    def admin_delete_flavor(view: CustomGenericViewSet, request, kwargs):
        flavor_id = kwargs[view.lookup_field]
        user = request.user

        try:
            flavor = Flavor.objects.filter(id=flavor_id).first()
            if flavor is None:
                raise exceptions.TargetNotExist(message=_('配置样式不存在'))

            old_service = flavor.service
            if not user.is_federal_admin():
                if not (old_service and old_service.user_has_perm(user)):
                    raise exceptions.AccessDenied(message=_('你没有此配置样式的管理权限'))

            flavor.delete()
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data=None, status=204)
