from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors as exceptions
from service.managers import ServiceManager
from servers.models import Flavor
from api.viewsets import CustomGenericViewSet
from api.serializers import server as server_serializers
from .handlers import serializer_error_msg


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
