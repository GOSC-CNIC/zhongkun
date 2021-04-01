import random
import requests
from io import BytesIO

from django.core.validators import validate_ipv4_address, ValidationError
from django.utils.translation import gettext_lazy, gettext as _
from django.http.response import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import Serializer
from rest_framework.reverse import reverse
from rest_framework.utils.urls import replace_query_param
from rest_framework import exceptions as drf_exceptions
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView, TokenObtainPairView

from servers.models import Server, Flavor, ServerArchive
from service.managers import ServiceManager
from service.models import ServiceConfig, DataCenter
from adapters import inputs, outputs
from core.quota import QuotaAPI
from core import request as core_request
from . import exceptions
from . import serializers
from .viewsets import CustomGenericViewSet, str_to_int_or_default
from .paginations import ServersPagination, DefaultPageNumberPagination
from core.taskqueue import server_build_status
from . import handlers


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
    except Exception:
        pass

    return msg


def is_ipv4(value):
    """
    是否是ipv4

    :param value:
    :return:
        True    # 是
        False   # 不是
    """
    if not value:
        return False

    try:
        validate_ipv4_address(value)
    except ValidationError as e:
        return False

    return True


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
                type=openapi.TYPE_STRING,
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
              "next": "http://xxx/api/server/?page=2&page_size=2",
              "previous": null,
              "servers": [
                {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "name": "gosc-instance-1cbaf0fd-20c1-4632-8e0c-7be8708591ac",
                  "vcpus": 1,
                  "ram": 1024,
                  "ipv4": "10.0.200.249",
                  "public_ip": false,
                  "image": "centos8_gui",
                  "creation_time": "2020-11-02T07:47:39.776384Z",
                  "remarks": "",
                  "endpoint_url": "http://159.226.235.16/",
                  "service": {
                    "id": "2",
                    "name": "怀柔204机房",
                    "service_type": "evcloud"
                  },
                  "user_quota": {           # may be null
                    "id": "1",
                    "tag": {
                      "value": 1,
                      "display": "普通配额"
                    },
                    "expiration_time": "2020-11-02T07:47:39.776384Z",       # may be null,
                    "deleted": false,
                    "display": "[普通配额](vCPU: 10, RAM: 10240Mb, PublicIP: 5, PrivateIP: 7)"
                  },
                  "center_quota": 2         # 1: 服务的私有资源配额，"user_quota"=null; 2: 服务的分享资源配额
                }
              ]
            }
        """
        servers = Server.objects.select_related('service', 'user_quota').filter(user=request.user)
        service_id = request.query_params.get('service_id', None)
        if service_id:
            servers = servers.filter(service_id=service_id)

        paginator = ServersPagination()
        page = paginator.paginate_queryset(servers, request, view=self)
        services = ServiceConfig.objects.select_related('data_center').all()
        service_id_map = {}
        for s in services:
            service_id_map[s.id] = s

        serializer = serializers.ServerSerializer(page, many=True, context={'service_id_map': service_id_map})
        return paginator.get_paginated_response(data=serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建服务器实例'),
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
        remarks = data.get('remarks') or request.user.username
        quota_id = data.get('quota_id', None)

        if not quota_id:
            exc = exceptions.BadRequest(message=_('必须提交"quota_id"参数'))
            return Response(exc.err_data(), status=exc.status_code)

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
            user_quota = QuotaAPI().server_create_quota_apply(
                service=service, user=request.user, vcpu=flavor.vcpus, ram=flavor.ram,
                public_ip=is_public_network, user_quota_id=quota_id)
        except exceptions.Error as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        params = inputs.ServerCreateInput(ram=flavor.ram, vcpu=flavor.vcpus, image_id=image_id,
                                          region_id=service.region_id, network_id=network_id, remarks=remarks)
        try:
            out = self.request_service(service=service, method='server_create', params=params)
        except exceptions.APIException as exc:
            try:
                QuotaAPI().server_quota_release(service=service, user=request.user,
                                                vcpu=flavor.vcpus, ram=flavor.ram, public_ip=is_public_network,
                                                user_quota_id=user_quota.id)
            except exceptions.Error:
                pass
            return Response(data=exc.err_data(), status=exc.status_code)

        out_server = out.server
        kwargs = {'center_quota': Server.QUOTA_PRIVATE}
        server = Server(service=service,
                        instance_id=out_server.uuid,
                        remarks=remarks,
                        user=request.user,
                        vcpus=flavor.vcpus,
                        ram=flavor.ram,
                        task_status=Server.TASK_IN_CREATING,
                        user_quota=user_quota,
                        public_ip=is_public_network,
                        **kwargs
                        )
        server.save()
        if service.service_type == service.SERVICE_EVCLOUD:
            if self._update_server_detail(server):
                return Response(data={'id': server.id}, status=status.HTTP_201_CREATED)

        server_build_status.creat_task(server)      # 异步任务查询server创建结果，更新server信息和创建状态
        return Response(data={'id': server.id}, status=status.HTTP_202_ACCEPTED)

    @staticmethod
    def _update_server_detail(server, task_status: int = None):
        try:
            return core_request.update_server_detail(server=server, task_status=task_status)
        except exceptions.Error as e:
            pass

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务器实例信息'),
        responses={
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询服务器实例信息

            http code 200:
            {
              "server": {
                "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                "name": "bfbdcbce3e904615af49377fdc2f2ea9",
                "vcpus": 1,
                "ram": 1024,
                "ipv4": "10.0.201.2",
                "public_ip": false,
                "image": "CentOS_8",
                "creation_time": "2020-09-23T07:10:14.009418Z",
                "remarks": "",
                "endpoint_url": "http://159.226.235.16/",
                "service": {
                    "id": "2",
                    "name": "怀柔204机房",
                    "service_type": "evcloud"
                },
                "user_quota": {           # may be null
                    "id": "1",
                    "tag": {
                      "value": 1,
                      "display": "普通配额"
                    },
                    "expiration_time": "2020-11-02T07:47:39.776384Z",       # may be null,
                    "deleted": false,
                    "display": "[普通配额](vCPU: 10, RAM: 10240Mb, PublicIP: 5, PrivateIP: 7)"
                },
                "center_quota": 2         # 1: 服务的私有资源配额，"user_quota"=null; 2: 服务的分享资源配额
              }
            }
        """
        server_id = kwargs.get(self.lookup_field, '')

        try:
            server = self.get_server(server_id=server_id, user=request.user,
                                     related_fields=['service__data_center'])
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

        if server.do_archive():     # 记录归档
            self.release_server_quota(server=server)    # 释放资源配额

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('操作服务器'),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'action': openapi.Schema(
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
        """
        服务器状态查询

            status code:
                0       # no state
                1       # the domain is running
                2       # the domain is blocked on resource
                3       # the domain is paused by user
                4       # the domain is being shut down
                5       # the domain is shut off
                6       # the domain is crashed
                7       # the domain is suspended by guest power management
                9       # host connect failed
                10      # domain miss
                11      # The domain is being built
                12      # Failed to build the domain
        """
        server_id = kwargs.get(self.lookup_field, '')

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        try:
            status_code, status_text = core_request.server_status_code(server=server)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if status_code in outputs.ServerStatus.normal_values():     # 虚拟服务器状态正常
            if (server.task_status == server.TASK_IN_CREATING) or (not is_ipv4(server.ipv4)):   #
                self._update_server_detail(server, task_status=server.TASK_CREATED_OK)

        if status_code == outputs.ServerStatus.NOSTATE and server.task_status == server.TASK_IN_CREATING:
            status_code = outputs.ServerStatus.BUILDING
            status_text = outputs.ServerStatus.get_mean(status_code)

        return Response(data={
            'status': {
                'status_code': status_code,
                'status_text': status_text
            }
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务器VNC'),
        responses={
            200: '''
                {
                  "vnc": {
                    "url": "xxx",           # 服务提供者url
                    "proxy_vnc": "xxx"      # 中间件代理url，可以访问内网服务；vmware服务没有此内容
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

        proxy_vnc = request.build_absolute_uri('/vms/vnc/')
        proxy_vnc = f'{proxy_vnc}?proxy={vnc}'
        # proxy_vnc = replace_query_param(url=proxy_vnc, key='proxy', val=vnc)
        return Response(data={'vnc': {
            'url': vnc,
            'proxy_url': proxy_vnc
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
            "400, 403, 404, 500": """
                {
                    "code": "AccessDenied", # ServerNotExist, "InternalError"
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
            return self.exception_reponse(
                exceptions.InvalidArgument(message='query param "remark" is required'))

        try:
            server = self.get_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        try:
            server.remarks = remarks
            server.save(update_fields=['remarks'])
        except Exception as exc:
            return self.exception_reponse(exc)

        return Response(data={'remarks': remarks})

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ServerCreateSerializer

        return Serializer

    @staticmethod
    def get_server(server_id: str, user, related_fields: list = None):
        fields = ['service', 'user_quota']
        if related_fields:
            for f in related_fields:
                if f not in fields:
                    fields.append(f)

        server = Server.objects.filter(id=server_id).select_related(*fields).first()
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
            QuotaAPI().server_quota_release(service=server.service, user=server.user,
                                            vcpu=server.vcpus, ram=server.ram, public_ip=server.public_ip,
                                            user_quota_id=server.user_quota_id)
        except exceptions.Error as e:
            return False

        return True


class ImageViewSet(CustomGenericViewSet):
    """
    系统镜像视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'id'
    lookup_value_regex = '[0-9a-z-]+'
    serializer_class = Serializer

    @swagger_auto_schema(
        operation_summary=gettext_lazy('镜像列表'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务端点id'
            ),
        ],
        responses={
            200: """
                [
                  {
                    "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
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
    pagination_class = None
    lookup_field = 'network_id'
    lookup_value_regex = '[0-9a-z-]+'
    serializer_class = Serializer

    @swagger_auto_schema(
        operation_summary=gettext_lazy('网络列表'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务id'
            ),
        ],
        responses={
            200: """
                [
                  {
                    "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
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
                type=openapi.TYPE_STRING,
                required=True,
                description='服务id'
            ),
        ],
        responses={
            200: """
                  {
                    "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('vpn配置文件下载'),
    )
    @action(methods=['get', ], detail=True, url_path='config', url_name='vpn-config')
    def vpn_config(self, request, *args, **kwargs):
        """
        vpn配置文件下载
        """
        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        url = self.request_vpn_service(service, 'get_vpn_config_file_url')
        r = requests.get(url)
        if r.status_code == 200:
            response = FileResponse(BytesIO(r.content), as_attachment=True, filename='config')
            response['Content-Type'] = r.headers.get('content-type')
            response['Content-Disposition'] = r.headers.get('content-disposition')
            return response

        return self.exception_reponse(exceptions.Error(message=str(r.content)))

    @swagger_auto_schema(
        operation_summary=gettext_lazy('vpn ca证书文件下载'),
    )
    @action(methods=['get', ], detail=True, url_path='ca', url_name='vpn-ca')
    def vpn_ca(self, request, *args, **kwargs):
        """
        vpn ca证书文件下载
        """
        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        url = self.request_vpn_service(service, 'get_vpn_ca_file_url')
        r = requests.get(url)
        if r.status_code == 200:
            response = FileResponse(BytesIO(r.content), as_attachment=True, filename='ca')
            response['Content-Type'] = r.headers.get('content-type')
            response['Content-Disposition'] = r.headers.get('content-disposition')
            return response

        return self.exception_reponse(exceptions.Error(message=str(r.content)))

    def get_serializer_class(self):
        return Serializer

    def get_permissions(self):
        if self.action in []:
            return []

        return super().get_permissions()


class FlavorViewSet(CustomGenericViewSet):
    """
    Flavor相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None

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
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
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


class UserQuotaViewSet(CustomGenericViewSet):
    """
    用户资源配额相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户资源配额'),
        manual_parameters=[
            openapi.Parameter(
                name='service',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=_('服务id, 过滤服务可用的资源配额')
            ),
            openapi.Parameter(
                name='usable',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description=_('true(过滤)，其他值（忽略）, 过滤可用的资源配额, 未过期的')
            )
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户资源配额

            Http Code: 状态码200，返回数据：
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "tag": {
                    "value": 1,             # 1: 普通配额； 2：试用配额
                    "display": "普通配额"
                  },
                  "user": {
                    "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
                    "username": "shun"
                  },
                  "service": {
                    "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
                    "name": "怀柔204机房"
                  },
                  "private_ip_total": 5,
                  "private_ip_used": 2,
                  "public_ip_total": 5,
                  "public_ip_used": 0,
                  "vcpu_total": 10,
                  "vcpu_used": 3,
                  "ram_total": 10240,       # Mb
                  "ram_used": 4176,
                  "disk_size_total": 0,     # Gb
                  "disk_size_used": 0,
                  "expiration_time": null,
                  "deleted": false,
                  "display": "[普通配额](vCPU: 10, RAM: 10240Mb, PublicIP: 5, PrivateIP: 5)"
                }
              ]
            }
        """
        return handlers.UserQuotaHandler.list_quotas(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举资源配额下的虚拟服务器'),
        manual_parameters=[
            openapi.Parameter(
                name='page',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('分页页码')
            ),
            openapi.Parameter(
                name='page_size',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('每页返回数据数量')
            ),
        ],
        responses={
        }
    )
    @action(methods=['get'], detail=True, url_path='servers', url_name='quota-servers')
    def quota_servers(self, request, *args, **kwargs):
        """
        列举资源配额下的虚拟服务器

            http code 200:
            {
              "count": 3,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "a24d4686-646a-11eb-b974-c8009fe2eb10",
                  "name": "6c8e17d2-6387-48b5-be1c-d7f845a7ae57",
                  "vcpus": 1,
                  "ram": 1024,
                  "ipv4": "10.0.200.235",
                  "public_ip": false,
                  "image": "cirros",
                  "creation_time": "2021-02-01T08:51:11.784626Z",
                  "remarks": ""
                }
              ]
            }
        """
        return handlers.UserQuotaHandler.list_quota_servers(view=self, request=request, kwargs=kwargs)


class ServiceViewSet(CustomGenericViewSet):
    """
    接入的服务
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举已接入的服务'),
        manual_parameters=[
            openapi.Parameter(
                name='center_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='联邦成员机构id'
            ),
            openapi.Parameter(
                name='available_only',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='只查询用户由资源可使用的服务，提交此参数即有效（不需要赋值）'
            ),
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举已接入的服务

            Http Code: 状态码200，返回数据：
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "name": "vmware(10.0.200.243)",
                  "service_type": "vmware",
                  "add_time": "2020-10-16T09:01:44.402955Z",
                  "need_vpn": false,
                  "status": 1,              # 1: 开启状态；2: 关闭状态;
                  "data_center": {
                    "id": 3,
                    "name": "VMware测试中心"
                  }
                }
              ]
            }
        """
        center_id = request.query_params.get('center_id', None)
        available_only = request.query_params.get('available_only', None)
        user = None if available_only is None else request.user

        queryset = ServiceManager().filter_service(center_id=center_id, user=user)
        paginator = self.pagination_class()
        try:
            quotas = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ServiceSerializer(quotas, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

        return response


class DataCenterViewSet(CustomGenericViewSet):
    """
    联邦成员机构
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦成员机构注册表'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        联邦成员机构注册表

            Http Code: 状态码200，返回数据：
            {
              "registries": [
                {
                  "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
                  "name": "网络中心",
                  "endpoint_vms": http://xxx/,
                  "endpoint_object": http://xxx/,
                  "endpoint_compute": http://xxx/,
                  "endpoint_monitor": http://xxx/,
                  "creation_time": 2021-02-07T06:20:00Z,
                  "status": {
                    "code": 1,
                    "message": "开启状态"
                  },
                  "desc": ""
                }
              ]
            }
        """
        try:
            queryset = DataCenter.objects.all()
            serializer = serializers.DataCenterSerializer(queryset, many=True)
            data = {
                'registries': serializer.data
            }
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

        return Response(data=data)


class JWTObtainPairView(TokenObtainPairView):
    """
    JWT登录认证视图
    """

    @swagger_auto_schema(
        operation_summary='登录认证，获取JWT',
        responses={
            200: ''''''
        }
    )
    def post(self, request, *args, **kwargs):
        """
        登录认证，获取JWT

            http 200:
            {
              "refresh": "xxx",     # refresh JWT, 此JWT通过刷新API可以获取新的access JWT
              "access": "xxx"       # access JWT, 用于身份认证，如 'Authorization JWT accessJWT'
            }
            http 401:
            {
              "code": "AuthenticationFailed",
              "message": "No active account found with the given credentials"
            }

            usage: in header "Authorization", example:
                Authorization: JWT <access token>
        """
        try:
            return super().post(request, args, kwargs)
        except drf_exceptions.AuthenticationFailed as exc:
            err = exceptions.AuthenticationFailed(message=str(exc))
            return Response(data=err.err_data(), status=err.status_code)


class JWTRefreshView(TokenRefreshView):
    """
    Refresh JWT视图
    """
    @swagger_auto_schema(
        operation_summary='刷新access JWT',
        responses={
            200: '''
                {
                  "access": "xxx"
                }
            '''
        }
    )
    def post(self, request, *args, **kwargs):
        """
        通过refresh JWT获取新的access JWT

            http 200:
            {
              "access": "xxx"
            }
            http 401:
            {
              "code": "InvalidJWT",
              "message": "Token is invalid or expired"
            }
        """
        try:
            return super().post(request, args, kwargs)
        except drf_exceptions.AuthenticationFailed as exc:
            if hasattr(exc, 'default_detail'):
                msg = exc.default_detail
            else:
                msg = str(exc)

            err = exceptions.InvalidJWT(message=msg)
            return Response(data=err.err_data(), status=err.status_code)


class JWTVerifyView(TokenVerifyView):
    """
    校验access JWT视图
    """

    @swagger_auto_schema(
        operation_summary='校验access JWT是否有效',
        responses={
            200: '''{ }'''
        }
    )
    def post(self, request, *args, **kwargs):
        """
        校验access JWT是否有效

            http 200:
            {
            }
            http 401:
            {
              "code": "InvalidJWT",
              "message": "Token is invalid or expired"
            }
        """
        try:
            return super().post(request, args, kwargs)
        except drf_exceptions.AuthenticationFailed as exc:
            if hasattr(exc, 'default_detail'):
                msg = exc.default_detail
            else:
                msg = str(exc)

            err = exceptions.InvalidJWT(message=msg)
            return Response(data=err.err_data(), status=err.status_code)


class ServerArchiveViewSet(CustomGenericViewSet):
    """
    虚拟服务器归档记录相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户虚拟服务器归档记录'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户虚拟服务器归档记录

            Http Code: 状态码200，返回数据：
                {
                  "count": 39,
                  "next": null,
                  "previous": null,
                  "results": [
                    {
                      "id": "6184d5b2-6468-11eb-8b43-c8009fe2eb10",
                      "name": "d1ddd55a-1fdc-44d6-bd71-d6e8b5c94bf9",
                      "vcpus": 1,
                      "ram": 80,
                      "ipv4": "10.0.200.240",
                      "public_ip": false,
                      "image": "cirros",
                      "creation_time": "2021-02-01T08:35:04.153252Z",
                      "remarks": "",
                      "service": {
                        "id": "3",
                        "name": "10.0.200.215",
                        "service_type": "openstack"
                      },
                      "user_quota": {
                        "id": "1",
                        "tag": {
                          "value": 1,
                          "display": "普通配额"
                        },
                        "expiration_time": null,
                        "deleted": false,
                        "display": "[普通配额](vCPU: 10, RAM: 10240Mb, PublicIP: 5, PrivateIP: 7)"
                      },
                      "center_quota": 2,
                      "user_quota_tag": 1,
                      "deleted_time": "2021-02-01T08:35:04.154218Z"
                    }
                  ]
                }
        """
        try:
            queryset = ServerArchive.objects.select_related('service').filter(user=request.user).all()
            paginator = self.pagination_class()
            servers = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ServerArchiveSerializer(servers, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

