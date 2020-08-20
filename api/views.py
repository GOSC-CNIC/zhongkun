from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from servers.models import Server
from vpn.models import VPNAuth
from . import exceptions, auth
from . import serializers
from .viewsets import CustomGenericViewSet, str_to_int_or_default


def serializer_error_msg(errors, default=''):
    """
    获取一个错误信息

    :param errors: serializer.errors
    :param default:
    :return:
        str
    """
    msg = default
    try:
        if isinstance(errors, list):
            for err in errors:
                msg = str(err)
                break
        elif isinstance(errors, dict):
            for key in errors:
                val = errors[key]
                msg = f'{key}, {str(val[0])}'
                break
    except:
        pass

    return msg


class ServersViewSet(CustomGenericViewSet):
    """
    虚拟服务器实例视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = LimitOffsetPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    # @swagger_auto_schema(
    #     operation_summary=gettext_lazy('服务器列表'),
    # )
    # def list(self, request, *args, **kwargs):
    #     servers_qs = Server.objects.filter(user=request.user, deleted=False).all()

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建服务器实例'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='服务端点id'
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            exc = exceptions.BadRequest(msg)
            return Response(data=exc.err_data(), status=exc.status_code)

        data = serializer.validated_data
        image_id = data.get('image_id', '')
        flavor_id = str_to_int_or_default(data.get('flavor_id', 0), 0)
        network_id = data.get('network_id', '')
        remarks = data.get('remarks', request.user.username)

        try:
            service = self.get_service(request, in_='body')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        try:
            r = self.request_service(service=service, method='server_create', region_id=service.region_id,
                                     image_id=image_id, flavor_id=flavor_id, network_id=network_id,
                                     extra_kwargs={
                                        'remarks': remarks
                                     })
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        vm_values = r['vm']
        server = Server(service=service,
                        instance_id=vm_values['uuid'],
                        flavor_id=flavor_id,
                        image_id=image_id,
                        remarks=remarks,
                        user=request.user
                        )
        server.save()

        try:
            server.name = vm_values['name']
            server.vcpus = vm_values['vcpu']
            server.ram = vm_values['mem']
            server.ipv4 = vm_values['mac_ip']
            server.image = vm_values['image']
            server.save()
        except Exception:
            pass

        return Response(data={'id': server.id})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除服务器实例')
    )
    def destroy(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        service = server.service
        try:
            self.request_service(service, method='server_delete', server_id=server.instance_id)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        server.do_soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('操作服务器'),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'op': openapi.Schema(
                    title='操作',
                    type=openapi.TYPE_STRING,
                    enum=['start', 'reboot', 'shutdown', 'poweroff', 'delete', 'delete_force'],
                    description="操作选项",
                )
            }
        ),
        responses={
            200: '''
                {
                    'code': 200,
                    'code_text': '操作成功'
                }
                '''
        }
    )
    @action(methods=['post'], url_path='action', detail=True, url_name='server-action')
    def server_action(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')
        try:
            op = request.data.get('op', None)
        except Exception as e:
            exc = exceptions.InvalidArgument(_('参数有误') + ',' + str(e))
            return Response(data=exc.err_data(), status=exc.status_code)

        ops = ['start', 'reboot', 'shutdown', 'poweroff', 'delete', 'delete_force']
        if not op or op not in ops:
            exc = exceptions.InvalidArgument(_('op参数无效'))
            return Response(data=exc.err_data(), status=exc.status_code)

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        service = server.service
        try:
            r = self.request_service(service, method='server_action', server_id=server.instance_id, op=op)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if op in ['delete', 'delete_force']:
            server.do_soft_delete()
        return Response({'code': 'OK', 'message': 'Success'})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务器状态查询'),
        responses={
            200: '''
                {
                }
                '''
        }
    )
    @action(methods=['get'], url_path='status', detail=True, url_name='server_status')
    def server_status(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        service = server.service
        try:
            r = self.request_service(service, method='server_status', server_id=server.instance_id)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        return Response(data=r)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务器VNC'),
        responses={
            200: '''
                    {
                    }
                    '''
        }
    )
    @action(methods=['get'], url_path='vnc', detail=True, url_name='server_vnc')
    def server_vnc(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        service = server.service
        try:
            r = self.request_service(service, method='server_vnc', server_id=server.instance_id)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        return Response(data=r)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ServerCreateSerializer

        return Serializer

    @staticmethod
    def get_server(server_id: int, user):
        server = Server.objects.filter(id=server_id, deleted=False).select_related('service', 'user').first()
        if not server:
            raise exceptions.NotFound(_('服务器实例不存在'))

        if not server.user_has_perms(user):
            raise exceptions.AccessDenied(_('无权限访问此服务器实例'))

        return server


class ImageViewSet(CustomGenericViewSet):
    """
    系统镜像视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = LimitOffsetPagination
    lookup_field = 'id'
    lookup_value_regex = '[0-9a-z-]+'
    serializer_class = Serializer

    @swagger_auto_schema(
        operation_summary=gettext_lazy('镜像列表'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='服务端点id'
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        try:
            r = self.request_service(service, method='list_images', region_id=service.region_id)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        return Response(data=r['results'])


class NetworkViewSet(CustomGenericViewSet):
    """
    网络子网视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = LimitOffsetPagination
    lookup_field = 'id'
    lookup_value_regex = '[0-9a-z-]+'
    serializer_class = Serializer

    @swagger_auto_schema(
        operation_summary=gettext_lazy('网络列表'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='服务id'
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        try:
            r = self.request_service(service, method='list_networks', region_id=service.region_id)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        return Response(data=r['results'])


class VPNViewSet(CustomGenericViewSet):
    """
    VPN相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None

    @swagger_auto_schema(
        operation_summary=gettext_lazy('获取VPN口令'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        获取VPN口令信息

            Http Code: 状态码200，返回数据：
            {
                "vpn": {
                    "id": 2,
                    "password": "2523c77e7b",
                    "created_time": "2020-03-04T06:01:50+00:00",
                    "modified_time": "2020-03-04T06:01:50+00:00",
                    "user": {
                        "id": 3,
                        "username": "869588058@qq.com"
                    }
                }
            }
        """
        vpn, created = VPNAuth.objects.get_or_create(user=request.user)
        return Response(data={'vpn': serializers.VPNSerializer(vpn).data})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改vpn口令'),
        responses={
            status.HTTP_201_CREATED: """
                {
                    "vpn": {
                        "id": 2,
                        "password": "2523c77e7b",
                        "created_time": "2020-03-04T06:01:50+00:00",
                        "modified_time": "2020-03-04T06:01:50+00:00",
                        "user": {
                            "id": 3,
                            "username": "869588058@qq.com"
                        }
                    }
                }
            """,
            status.HTTP_400_BAD_REQUEST: """
                    {
                        "code": 'xxx',
                        "message": "xxx"
                    }
                """
        }
    )
    def create(self, request, *args, **kwargs):
        """
        修改vpn口令
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors, 'password error')
            exc = exceptions.BadRequest(msg)
            return Response(data=exc.err_data(), status=exc.status_code)

        password = serializer.validated_data['password']
        vpn, created = VPNAuth.objects.get_or_create(user=request.user)
        if vpn.reset_password(password):
            return Response(data={'vpn': serializers.VPNSerializer(vpn).data}, status=status.HTTP_201_CREATED)

        exc = exceptions.APIException(_('修改失败'))
        return Response(data=exc.err_data(), status=exc.status_code)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.VPNPostSerializer
        return Serializer


class FlavorViewSet(CustomGenericViewSet):
    """
    Flavor相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举配置样式flavor'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='服务id'
            )
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举配置样式flavor

            Http Code: 状态码200，返回数据：
            {
                "vpn": {
                    "id": 2,
                    "password": "2523c77e7b",
                    "created_time": "2020-03-04T06:01:50+00:00",
                    "modified_time": "2020-03-04T06:01:50+00:00",
                    "user": {
                        "id": 3,
                        "username": "869588058@qq.com"
                    }
                }
            }
        """
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        try:
            r = self.request_service(service, method='list_flavors')
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        return Response(data=r['results'])

