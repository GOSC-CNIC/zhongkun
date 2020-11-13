import random

from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import Serializer
from rest_framework.reverse import reverse
from rest_framework.utils.urls import replace_query_param
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from servers.models import Server, Flavor
from adapters import inputs, outputs
from core.quota import QuotaAPI
from . import exceptions
from . import serializers
from .viewsets import CustomGenericViewSet, str_to_int_or_default
from .paginations import ServersPagination


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
    pagination_class = ServersPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举服务器实例'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description='服务端点id'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举服务器实例

            200: {
              "count": 8,
              "next": null,
              "previous": null,
              "servers": [
                {
                  "id": 22,
                  "name": "gosc-instance-1cbaf0fd-20c1-4632-8e0c-7be8708591ac",
                  "vcpus": 1,
                  "ram": 1024,
                  "ipv4": "10.0.200.249",
                  "public_ip": false,
                  "image": "centos8_gui",
                  "creation_time": "2020-11-02T07:47:39.776384Z",
                  "remarks": ""
                }
              ]
            }
        """
        servers = Server.objects.filter(user=request.user)
        service_id = request.query_params.get('service_id', None)
        if service_id:
            try:
                service_id = int(service_id)
            except ValueError:
                exc = exceptions.InvalidArgument(message='Invalid query param "service_id"')
                return Response(data=exc.err_data(), status=exc.status_code)

            servers = servers.filter(service_id=service_id)

        paginator = ServersPagination()
        page = paginator.paginate_queryset(servers, request, view=self)
        serializer = serializers.ServerSerializer(page, many=True)
        return paginator.get_paginated_response(data=serializer.data)

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
        ],
        responses={
            201: '''    
                {
                    "id": "xxx"     # 服务器id; 创建成功
                }
            ''',
            202: '''
                {
                    "id": "xxx"     # 服务器id; 已接受创建请求，正在创建中；
                }            
            '''
        }
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

        flavor = Flavor.objects.filter(id=flavor_id).first()
        if not flavor:
            exc = exceptions.BadRequest(message=_('无效的flavor id'))
            return Response(exc.err_data(), status=exc.status_code)

        try:
            service = self.get_service(request, in_='body')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.NetworkDetailInput(network_id=network_id)
        try:
            out_net = self.request_service(service=service, method='network_detail', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        is_public_network = out_net.network.public

        # 资源配额扣除
        try:
            use_shared_quota, user_quota = QuotaAPI().server_create_quota_apply(
                data_center=service.data_center, user=request.user, vcpu=flavor.vcpus, ram=flavor.ram,
                public_ip=is_public_network)
        except exceptions.Error as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        params = inputs.ServerCreateInput(ram=flavor.ram, vcpu=flavor.vcpus, image_id=image_id,
                                          region_id=service.region_id, network_id=network_id, remarks=remarks)
        try:
            out = self.request_service(service=service, method='server_create', params=params)
        except exceptions.APIException as exc:
            try:
                QuotaAPI().server_quota_release(data_center=service.data_center, user=request.user,
                                                vcpu=flavor.vcpus, ram=flavor.ram, public_ip=is_public_network,
                                                use_shared_quota=use_shared_quota, user_quota_id=user_quota.id)
            except exceptions.Error:
                pass
            return Response(data=exc.err_data(), status=exc.status_code)

        out_server = out.server
        if use_shared_quota:
            kwargs = {'center_quota': Server.QUOTA_SHARED}
        else:
            kwargs = {'center_quota': Server.QUOTA_PRIVATE}
        server = Server(service=service,
                        instance_id=out_server.uuid,
                        remarks=remarks,
                        user=request.user,
                        vcpus=flavor.vcpus,
                        ram=flavor.ram,
                        task_status=Server.TASK_IN_CREATING,
                        user_quota=user_quota,
                        **kwargs
                        )
        server.save()
        if service.service_type == service.SERVICE_EVCLOUD:
            if self._update_server_detail(server):
                return Response(data={'id': server.id}, status=status.HTTP_201_CREATED)

        return Response(data={'id': server.id}, status=status.HTTP_202_ACCEPTED)

    def _update_server_detail(self, server, task_status: int = None):
        """
        尝试更新服务器的详细信息
        :param server:
        :param task_status: 设置server的创建状态；默认None忽略
        :return:
            True    # success
            False   # failed
        """
        # 尝试获取详细信息
        params = inputs.ServerDetailInput(server_id=server.instance_id)
        try:
            out = self.request_service(service=server.service, method='server_detail', params=params)
            out_server = out.server
        except exceptions.APIException as exc:      #
            return False

        try:
            server.name = out_server.name if out_server.name else out_server.uuid
            if out_server.vcpu:
                server.vcpus = out_server.vcpu
            if out_server.ram:
                server.ram = out_server.ram

            server.public_ip = out_server.ip.public_ipv4 if out_server.ip.public_ipv4 else False
            server.ipv4 = out_server.ip.ipv4 if out_server.ip.ipv4 else ''
            server.image = out_server.image.name
            if server.ipv4 and server.image:
                server.task_status = task_status if task_status is not None else server.TASK_CREATED_OK     # 创建成功
            server.save()
        except Exception as e:
            return False

        return True

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务器实例信息'),
        responses={
            200: """
            {
              "server": {
                "id": 13,
                "name": "bfbdcbce3e904615af49377fdc2f2ea9",
                "vcpus": 1,
                "ram": 1024,
                "ipv4": "10.0.201.2",
                "public_ip": false,
                "image": "CentOS_8",
                "creation_time": "2020-09-23T07:10:14.009418Z",
                "remarks": ""
              }
            }
            """
        }
    )
    def retrieve(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        # 如果元数据完整，各种服务不同概率去更新元数据
        if server.ipv4 and server.image:
            need_update = False
            if server.service.service_type == server.service.SERVICE_EVCLOUD:
                if random.choice(range(10)) == 0:
                    need_update = True
            elif server.service.service_type == server.service.SERVICE_OPENSTACK:
                if random.choice(range(5)) == 0:
                    need_update = True
            elif random.choice(range(2)) == 0:
                need_update = True

            if not need_update:
                serializer = serializers.ServerSerializer(server)
                return Response(data={'server': serializer.data})

        service = server.service
        params = inputs.ServerDetailInput(server_id=server.instance_id)
        try:
            out = self.request_service(service=service, method='server_detail', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        update_fields = []
        new_vcpu = out.server.vcpu
        if new_vcpu and server.vcpus != new_vcpu:
            server.vcpus = new_vcpu
            update_fields.append('vcpus')

        new_ram = out.server.ram
        if new_ram and server.ram != new_ram:
            server.ram = new_ram
            update_fields.append('ram')

        new_ipv4 = out.server.ip.ipv4
        if new_ipv4 and server.ipv4 != new_ipv4:
            server.ipv4 = new_ipv4
            update_fields.append('ipv4')

        new_name = out.server.image.name
        if new_name and server.image != new_name:
            server.image = new_name
            update_fields.append('image')

        new_pub = out.server.ip.public_ipv4
        if new_pub is not None and server.public_ip != new_pub:
            server.public_ip = new_pub
            update_fields.append('public_ip')

        if update_fields:
            try:
                server.save(update_fields=update_fields)
            except Exception as e:
                pass

        serializer = serializers.ServerSerializer(server)
        return Response(data={'server': serializer.data})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除服务器实例'),
        manual_parameters=[
            openapi.Parameter(
                name='force',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='强制删除'
            ),
        ],
        responses={
            204: """NO CONTENT""",
            403: """
                {
                    "code": "AccessDenied",
                    "message": "xxx"
                }
                """,
            404: """
                {
                    "code": "ServerNotExist",
                    "message": "xxx"
                }
                """,
            500: """
                {
                    "code": "InternalError",
                    "message": "xxx"
                }
                """
        }
    )
    def destroy(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')
        q_force = request.query_params.get('force', '')
        if q_force.lower() == 'true':
            force = True
        else:
            force = False
        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        params = inputs.ServerDeleteInput(server_id=server.instance_id, force=force)
        try:
            self.request_service(server.service, method='server_delete', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        server.do_archive()     # 记录归档
        self.release_server_quota(server=server)    # 释放资源配额

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
            200: """
                {
                    "action": "xxx"
                }
                """,
            400: """
                {
                    "code": "InvalidArgument",
                    "message": "xxx"
                }
                """,
            500: """
                {
                    "code": "InternalError",
                    "message": "xxx"
                }
                """
        }
    )
    @action(methods=['post'], url_path='action', detail=True, url_name='server-action')
    def server_action(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')
        try:
            act = request.data.get('action', None)
        except Exception as e:
            exc = exceptions.InvalidArgument(_('参数有误') + ',' + str(e))
            return Response(data=exc.err_data(), status=exc.status_code)

        actions = inputs.ServerAction.values    # ['start', 'reboot', 'shutdown', 'poweroff', 'delete', 'delete_force']
        if act is None:
            exc = exceptions.InvalidArgument(_('action参数是必须的'))
            return Response(data=exc.err_data(), status=exc.status_code)

        if act not in actions:
            exc = exceptions.InvalidArgument(_('action参数无效'))
            return Response(data=exc.err_data(), status=exc.status_code)

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        params = inputs.ServerActionInput(server_id=server.instance_id, action=act)
        service = server.service
        try:
            r = self.request_service(service, method='server_action', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if act in ['delete', 'delete_force']:
            server.do_archive()
            self.release_server_quota(server=server)    # 释放资源配额

        return Response({'action': act})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务器状态查询'),
        responses={
            200: """
                {
                  "status": {
                    "status_code": 1,
                    "status_text": "running"
                  }
                }
                """,
            403: """
                {
                    "code": "AccessDenied",
                    "message": "xxx"
                }
                """,
            404: """
                    {
                        "code": "ServerNotExist",
                        "message": "xxx"
                    }
                    """,
            500: """
                {
                    "code": "InternalError",
                    "message": "xxx"
                }
                """
        }
    )
    @action(methods=['get'], url_path='status', detail=True, url_name='server_status')
    def server_status(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        params = inputs.ServerStatusInput(server_id=server.instance_id)
        service = server.service
        try:
            r = self.request_service(service, method='server_status', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        status_code = r.status
        if status_code in outputs.ServerStatus.normal_values():     # 虚拟服务器状态正常
            if (server.task_status == server.TASK_IN_CREATING) or (not server.ipv4):   #
                self._update_server_detail(server, task_status=server.TASK_CREATED_OK)

        return Response(data={
            'status': {
                'status_code': status_code,
                'status_text': r.status_mean
            }
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务器VNC'),
        responses={
            200: '''
                {
                  "vnc": {
                    "url": "xxx"
                  }
                }
                ''',
            403: """
                {
                    "code": "AccessDenied",
                    "message": "xxx"
                }
                """,
            404: """
                {
                    "code": "ServerNotExist",
                    "message": "xxx"
                }
                """,
            500: """
                {
                    "code": "InternalError",
                    "message": "xxx"
                }
                """
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
        params = inputs.ServerVNCInput(server_id=server.instance_id)
        try:
            r = self.request_service(service, method='server_vnc', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        vnc = r.vnc.url
        if not vnc.startswith('http') and service.service_type == service.SERVICE_VMWARE:
            path = reverse('servers:vmware')
            url = request.build_absolute_uri(location=path)
            vnc = replace_query_param(url=url, key='vm_url', val=r.vnc.url)

        return Response(data={'vnc': {
            'url': vnc
        }})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改云服务器备注信息'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='remark',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='新的备注信息'
            )
        ],
        responses={
            200: '''
                {
                    "remarks": "xxx"
                }
            ''',
            403: """
                    {
                        "code": "AccessDenied",
                        "message": "xxx"
                    }
                    """,
            404: """
                    {
                        "code": "ServerNotExist",
                        "message": "xxx"
                    }
                    """,
            500: """
                    {
                        "code": "InternalError",
                        "message": "xxx"
                    }
                    """
        }
    )
    @action(methods=['patch'], url_path='remark', detail=True, url_name='server-remark')
    def server_remark(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')
        remarks = request.query_params.get('remark', None)
        if remarks is None:
            return Response(data=exceptions.InvalidArgument(message='query param "remark" is required'))

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        try:
            server.remarks = remarks
            server.save(update_fields=['remarks'])
        except Exception as exc:
            return Response(data=exceptions.APIException(extend_msg=str(exc)), status=500)

        return Response(data={'remarks': remarks})

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ServerCreateSerializer

        return Serializer

    @staticmethod
    def get_server(server_id: int, user):
        server = Server.objects.filter(id=server_id).select_related('service', 'user').first()
        if not server:
            raise exceptions.NotFound(_('服务器实例不存在'))

        if not server.user_has_perms(user):
            raise exceptions.AccessDenied(_('无权限访问此服务器实例'))

        return server

    @staticmethod
    def release_server_quota(server):
        """
        释放虚拟服务器资源配额

        :param server: 服务器对象
        :return:
            True
            False
        """
        try:
            QuotaAPI().server_quota_release(data_center=server.service.data_center, user=server.user,
                                            vcpu=server.vcpus, ram=server.ram, public_ip=server.public_ip,
                                            use_shared_quota=server.is_use_shared_quota, user_quota_id=server.user_quota_id)
        except exceptions.Error as e:
            return False

        return True


class ImageViewSet(CustomGenericViewSet):
    """
    系统镜像视图
    """
    permission_classes = [IsAuthenticated, ]
    # pagination_class = LimitOffsetPagination
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
        ],
        responses={
            200: """
                [
                  {
                    "id": "10",
                    "name": "空天院_ubuntu1804_radi",
                    "system": "空天院_ubuntu1804_radi",
                    "system_type": "Linux",
                    "creation_time": "2020-09-23T07:15:20.087505Z",
                    "desc": "空天院_ubuntu1804_radi"
                  }
                ]
            """
        }
    )
    def list(self, request, *args, **kwargs):
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.ListImageInput(region_id=service.region_id)
        try:
            r = self.request_service(service, method='list_images', params=params)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.ImageSerializer(r.images, many=True)
        return Response(data=serializer.data)


class NetworkViewSet(CustomGenericViewSet):
    """
    网络子网视图
    """
    permission_classes = [IsAuthenticated, ]
    # pagination_class = LimitOffsetPagination
    lookup_field = 'network_id'
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
        ],
        responses={
            200: """
                [
                  {
                    "id": "2",
                    "name": "private_10.108.50.0",
                    "public": false,
                    "segment": "10.108.50.0"
                  }
                ]
            """
        }
    )
    def list(self, request, *args, **kwargs):
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.ListNetworkInput(region_id=service.region_id)
        try:
            r = self.request_service(service, method='list_networks', params=params)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.NetworkSerializer(r.networks, many=True)
        return Response(data=serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询网络信息'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='服务id'
            ),
        ],
        responses={
            200: """
                  {
                    "id": "2",
                    "name": "private_10.108.50.0",
                    "public": false,
                    "segment": "10.108.50.0"
                  }
                """
        }
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        network_id = kwargs.get(self.lookup_field)

        params = inputs.NetworkDetailInput(network_id=network_id)
        try:
            r = self.request_service(service, method='network_detail', params=params)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.NetworkSerializer(r.network)
        return Response(data=serializer.data)


class VPNViewSet(CustomGenericViewSet):
    """
    VPN相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'service_id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('获取VPN口令'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        获取VPN口令信息

            Http Code: 状态码200，返回数据：
            {
                "vpn": {
                    "username": "testuser",
                    "password": "password",
                    "active": true,
                    "create_time": "2020-07-29T15:12:08.715731+08:00",
                    "modified_time": "2020-07-29T15:12:08.715998+08:00"
                }
            }
        """
        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        try:
            r = self.request_vpn_service(service, method='get_vpn_or_create', username=request.user.username)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)
        return Response(data={'vpn': r})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改vpn口令'),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The new password of vpn'
                )
            }
        ),
        responses={
            status.HTTP_201_CREATED: """
                {
                    "vpn": {
                        "username": "testuser",
                        "password": "password",
                        "active": true,
                        "create_time": "2020-07-29T15:12:08.715731+08:00",
                        "modified_time": "2020-07-29T15:12:08.715998+08:00"
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
    def partial_update(self, request, *args, **kwargs):
        """
        修改vpn口令
        """
        password = request.data.get('password')

        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        try:
            r = self.request_vpn_service(service, method='vpn_change_password', username=request.user.username,
                                         password=password)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)
        return Response(data={'vpn': r})

    def get_serializer_class(self):
        return Serializer


class FlavorViewSet(CustomGenericViewSet):
    """
    Flavor相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    # pagination_class = LimitOffsetPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举配置样式flavor'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举配置样式flavor

            Http Code: 状态码200，返回数据：
            {
              "flavors": [
                {
                  "id": 4,
                  "vcpus": 4,
                  "ram": 4096
                }
              ]
            }
        """
        try:
            flavors = Flavor.objects.filter(enable=True).order_by('vcpus').all()
            serializer = serializers.FlavorSerializer(flavors, many=True)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

        return Response(data={"flavors": serializer.data})

