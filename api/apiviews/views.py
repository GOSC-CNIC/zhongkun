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
from rest_framework import parsers
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from servers.models import Server, Flavor
from servers.managers import ServerManager
from service.managers import ServiceManager
from service.models import DataCenter, ApplyOrganization, ApplyVmService
from adapters import inputs, outputs
from core.quota import QuotaAPI
from core import request as core_request
from core import errors as exceptions
from vo.models import VoMember
from api import serializers
from api.viewsets import CustomGenericViewSet
from api.paginations import ServersPagination, DefaultPageNumberPagination
from api.handlers import (
    handlers, ServerHandler, ServerArchiveHandler
)


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
        operation_summary=gettext_lazy('列举用户个人服务器实例，或者以管理员身份列举服务器实例'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='服务端点id'
            ),
            openapi.Parameter(
              name='ip-contain',
              in_=openapi.IN_QUERY,
              type=openapi.TYPE_STRING,
              required=False,
              description=gettext_lazy('过滤条件，查询ip地址中包含指定字符串的服务器')
            ),
            openapi.Parameter(
                name='user-id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('过滤条件，用户id，此参数只有以管理员身份请求时有效，否则400，不能与参数“vo-id”一起提交')
            ),
            openapi.Parameter(
              name='username',
              in_=openapi.IN_QUERY,
              type=openapi.TYPE_STRING,
              required=False,
              description=gettext_lazy('过滤条件，用户名，此参数只有以管理员身份请求时有效，否则400，不能与参数“vo-id”一起提交')
            ),
            openapi.Parameter(
                name='vo-id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('过滤条件，vo组id，此参数只有以管理员身份请求时有效，否则400 BadRequest')
            ),
        ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户个人服务器实例，或者以管理员身份列举服务器实例

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
                  "center_quota": 2,         # 1: 服务的私有资源配额，"user_quota"=null; 2: 服务的分享资源配额
                  "classification": "personal",
                  "vo_id": null,
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "lock": "free"    # 'free': 无锁；'lock-delete': 锁定删除，防止删除；'lock-operation', '锁定所有操作，只允许读'
                }
              ]
            }
        """
        return ServerHandler.list_servers(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举vo组的服务器实例'),
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
    @action(methods=['get'], detail=False, url_path='vo/(?P<vo_id>.+)')
    def list_vo_servers(self, request, *args, **kwargs):
        """
        列举vo组的服务器实例

            200: {
              "count": 8,
              "next": "https://xxx/api/server/vo/3d7cd5fc-d236-11eb-9da9-c8009fe2eb10/?page=2&page_size=2",
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
                  "endpoint_url": "https://159.226.235.16/",
                  "service": {
                    "id": "2",
                    "name": "怀柔204机房",
                    "service_type": "evcloud"
                  },
                  "center_quota": 2,         # 1: 服务的私有资源配额，"user_quota"=null; 2: 服务的分享资源配额
                  "classification": "vo"
                  "vo_id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "lock": "free"    # 'free': 无锁；'lock-delete': 锁定删除，防止删除；'lock-operation', '锁定所有操作，只允许读'
                }
              ]
            }
        """
        return ServerHandler.list_vo_servers(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建云服务器实例'),
        responses={
            200: '''    
                {
                    "order_id": "xxx",      # 订单id
                }
            '''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        * 预付费模式时，请求成功会创建一个待支付的订单，支付订单成功后，订购的资源才会创建交付；
        * 按量计费模式时，请求成功会创建一个已支付订单，订购的资源会立即创建交付；
        """
        return ServerHandler().server_order_create(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('续费云服务器实例'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='period',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('续费时长（月），不得与参数“renew_to_time”同时提交')
            ),
            openapi.Parameter(
                name='renew_to_time',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=_('续费到指定日期，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ，不得与参数“period”同时提交')
            )
        ],
        responses={
            200: '''    
                    {
                        "order_id": "xxx",      # 订单id
                    }
                '''
        }
    )
    @action(methods=['POST'], detail=True, url_path='renew', url_name='renew-server')
    def renew_server(self, request, *args, **kwargs):
        """
        续费包年包月预付费模式云服务器，请求成功会创建一个待支付的订单，支付订单成功后，会自动延长实例的过期时间
        """
        return ServerHandler().renew_server(view=self, request=request, kwargs=kwargs)

    @staticmethod
    def _update_server_detail(server, task_status: int = None):
        """
        :return:
            server      # success
            None        # failed
        """
        try:
            return core_request.update_server_detail(server=server, task_status=task_status)
        except exceptions.Error as e:
            pass

    @swagger_auto_schema(
        operation_summary=gettext_lazy('重建服务器实例, 更换系统'),
        responses={
            202: '''
                    {
                        "id": "xxx",     # 服务器id; 已接受创建请求，正在重建中；
                        "image_id": "xxx"
                    }            
                '''
        }
    )
    @action(methods=['post'], detail=True, url_path='rebuild', url_name='rebuild')
    def rebuild(self, request, *args, **kwargs):
        """
        重建服务器实例, 更换系统

            http code 202：已接受重建请求，正在重建中；
            {
                "id": "xxx",     # 服务器id;
                "image_id": "xxx"
            }
        """
        return ServerHandler.server_rebuild(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务器实例信息'),
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN,
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
                "endpoint_url": "https://159.226.235.16/",
                "service": {
                    "id": "2",
                    "name": "怀柔204机房",
                    "service_type": "evcloud"
                },
                "center_quota": 2,         # 1: 服务的私有资源配额，"user_quota"=null; 2: 服务的分享资源配额
                "classification": "vo",
                "vo_id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",    # null when "classification"=="personal"
                "user": {
                    "id": "1",
                    "username": "shun"
                },
                "lock": "free"    # 'free': 无锁；'lock-delete': 锁定删除，防止删除；'lock-operation', '锁定所有操作，只允许读'
              }
            }
        """
        server_id = kwargs.get(self.lookup_field, '')

        try:
            if self.is_as_admin_request(request=request):
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=request.user, related_fields=['service__data_center'],
                    as_admin=True)
            else:
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=request.user, related_fields=['service__data_center', 'vo__owner'])
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        # 如果元数据完整，各种服务不同概率去更新元数据
        if server.ipv4 and server.image:
            need_update = False
            if server.service.service_type == server.service.ServiceType.EVCLOUD:
                if random.choice(range(10)) == 0:
                    need_update = True
            elif server.service.service_type == server.service.ServiceType.OPENSTACK:
                if random.choice(range(5)) == 0:
                    need_update = True
            elif random.choice(range(2)) == 0:
                need_update = True

            if not need_update:
                serializer = serializers.ServerSerializer(server)
                return Response(data={'server': serializer.data})

        self._update_server_detail(server=server)
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
        ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN,
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
        """
        vo组云主机的删除需要vo组管理员权限
        """
        server_id = kwargs.get(self.lookup_field, '')
        q_force = request.query_params.get('force', '')
        if q_force.lower() == 'true':
            force = True
        else:
            force = False

        try:
            if self.is_as_admin_request(request=request):
                server = ServerManager().get_manage_perm_server(
                    server_id=server_id, user=request.user, related_fields=['service__data_center'], as_admin=True)
            else:
                server = ServerManager().get_manage_perm_server(
                    server_id=server_id, user=request.user, related_fields=['service__data_center', 'vo__owner'])
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if server.is_locked_delete():
            return self.exception_response(exceptions.ResourceLocked(
                message=_('无法删除，云主机已加锁锁定了删除')
            ))

        params = inputs.ServerDeleteInput(instance_id=server.instance_id, instance_name=server.instance_name,
                                          force=force)
        try:
            self.request_service(server.service, method='server_delete', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if server.do_archive(archive_user=request.user):     # 记录归档
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
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN,
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
        """
        vo组云主机的删除操作需要vo组管理员权限
        """
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

        need_manager_perm = False
        if act in [inputs.ServerAction.DELETE, inputs.ServerAction.DELETE_FORCE]:
            need_manager_perm = True

        try:
            if need_manager_perm:
                if self.is_as_admin_request(request=request):
                    server = ServerManager().get_manage_perm_server(
                        server_id=server_id, user=request.user, related_fields=['service__data_center'], as_admin=True)
                else:
                    server = ServerManager().get_manage_perm_server(
                        server_id=server_id, user=request.user, related_fields=['service__data_center', 'vo__owner'])

                if server.is_locked_delete():
                    return self.exception_response(exceptions.ResourceLocked(
                        message=_('无法删除，云主机已加锁锁定了删除')
                    ))
            else:
                if self.is_as_admin_request(request=request):
                    server = ServerManager().get_read_perm_server(
                        server_id=server_id, user=request.user, related_fields=['service__data_center'], as_admin=True)
                else:
                    server = ServerManager().get_read_perm_server(
                        server_id=server_id, user=request.user, related_fields=['service__data_center', 'vo__owner'])

                if server.is_locked_operation():
                    return self.exception_response(exceptions.ResourceLocked(
                        message=_('云主机已加锁锁定了任何操作')
                    ))
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        params = inputs.ServerActionInput(
            instance_id=server.instance_id, instance_name=server.instance_name, action=act)

        try:
            r = self.request_service(server.service, method='server_action', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if act in [inputs.ServerAction.DELETE, inputs.ServerAction.DELETE_FORCE]:
            server.do_archive(archive_user=request.user)
            self.release_server_quota(server=server)    # 释放资源配额

        return Response({'action': act})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务器状态查询'),
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN,
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
                13      # An error occurred in the domain.
        """
        def build_response(_status_code):
            status_text = outputs.ServerStatus.get_mean(_status_code)
            return Response(data={
                'status': {
                    'status_code': _status_code,
                    'status_text': status_text
                }
            })

        server_id = kwargs.get(self.lookup_field, '')

        try:
            if self.is_as_admin_request(request=request):
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=request.user, as_admin=True)
            else:
                server = ServerManager().get_read_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if server.task_status == server.TASK_CREATE_FAILED:
            return build_response(outputs.ServerStatus.BUILT_FAILED)

        try:
            status_code, status_text = core_request.server_status_code(server=server)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if status_code in outputs.ServerStatus.normal_values():     # 虚拟服务器状态正常
            if (server.task_status == server.TASK_IN_CREATING) or (not is_ipv4(server.ipv4)):
                self._update_server_detail(server, task_status=server.TASK_CREATED_OK)

        if server.task_status == server.TASK_IN_CREATING:
            if status_code == outputs.ServerStatus.NOSTATE:
                status_code = outputs.ServerStatus.BUILDING
            elif status_code in [outputs.ServerStatus.ERROR, outputs.ServerStatus.BUILT_FAILED]:
                server.task_status = server.TASK_CREATE_FAILED
                server.save(update_fields=['task_status'])
                status_code = outputs.ServerStatus.BUILT_FAILED

        return build_response(status_code)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务器VNC'),
        responses={
            200: '''
                {
                  "vnc": {
                    "url": "xxx"           # 服务提供者url
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
    @action(methods=['get'], url_path='vnc', detail=True, url_name='server-vnc')
    def server_vnc(self, request, *args, **kwargs):
        server_id = kwargs.get(self.lookup_field, '')

        try:
            server = ServerManager().get_read_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        service = server.service
        params = inputs.ServerVNCInput(instance_id=server.instance_id, instance_name=server.instance_name)
        try:
            r = self.request_service(service, method='server_vnc', params=params)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        vnc = r.vnc.url
        if not vnc.startswith('http') and (
                service.service_type in [service.ServiceType.VMWARE, service.ServiceType.UNIS_CLOUD]):
            path = reverse('servers:vmware')
            url = request.build_absolute_uri(location=path)
            vnc = replace_query_param(url=url, key='vm_url', val=r.vnc.url)
            vnc = replace_query_param(url=vnc, key='server-name', val=server.name)

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
        """
        vo组云主机需要vo组管理员权限
        """
        server_id = kwargs.get(self.lookup_field, '')
        remarks = request.query_params.get('remark', None)
        if remarks is None:
            return self.exception_response(
                exceptions.InvalidArgument(message='query param "remark" is required'))

        try:
            server = ServerManager().get_manage_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        if server.is_locked_operation():
            return self.exception_response(exceptions.ResourceLocked(
                message=_('云主机已加锁锁定了一切操作')
            ))

        try:
            server.remarks = remarks
            server.save(update_fields=['remarks'])
        except Exception as exc:
            return self.exception_response(exc)

        return Response(data={'remarks': remarks})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('云服务器锁设置'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='lock',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'{Server.Lock.choices}'
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
    @action(methods=['post'], url_path='lock', detail=True, url_name='server-lock')
    def server_lock(self, request, *args, **kwargs):
        """
        云服务器锁设置
        """
        return ServerHandler.server_lock(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ServerCreateSerializer
        elif self.action == 'rebuild':
            return serializers.ServerRebuildSerializer

        return Serializer

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
            QuotaAPI().server_quota_release(service=server.service, vcpu=server.vcpus,
                                            ram=server.ram, public_ip=server.public_ip)
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
            openapi.Parameter(
                name='azone_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='可用区编码，只列举可用区内的网络'
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
        azone_id = request.query_params.get('azone_id', None)
        if azone_id == '':
            return self.exception_response(
                exceptions.InvalidArgument(message='参数“azone_id”无效'))

        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.ListNetworkInput(region_id=service.region_id, azone_id=azone_id)
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

        return self.exception_response(exceptions.Error(message=str(r.content)))

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

        return self.exception_response(exceptions.Error(message=str(r.content)))

    def get_serializer_class(self):
        return Serializer

    def get_permissions(self):
        if self.action in ['vpn_config', 'vpn_ca']:
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


class ServiceViewSet(CustomGenericViewSet):
    """
    接入的服务
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举已接入的服务'),
        manual_parameters=[
            openapi.Parameter(
                name='center_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='联邦成员机构id'
            )
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
                  "name_en": "string",
                  "service_type": "vmware",
                  "cloud_type": "private",
                  "add_time": "2020-10-16T09:01:44.402955Z",
                  "need_vpn": false,
                  "status": "enable",              # enable: 开启状态；disable: 停止服务状态; deleted: 删除
                  "data_center": {
                    "id": 3,
                    "name": "VMware测试中心"
                  },
                  "longitude": 0,
                  "latitude": 0
                }
              ]
            }
        """
        return handlers.VmServiceHandler.list_services(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户有管理权限的服务'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='admin', url_name='admin-list')
    def admin_list(self, request, *args, **kwargs):
        """
        列举用户有管理权限的服务
        """
        service_qs = ServiceManager().get_has_perm_service(user=request.user)
        return self.paginate_service_response(request=request, qs=service_qs)

    @action(methods=[], detail=True, url_path='p-quota', url_name='private-quota')
    def private_quota(self, request, *args, **kwargs):
        pass

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改服务私有配额'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @private_quota.mapping.post
    def change_private_quota(self, request, *args, **kwargs):
        """
        修改服务私有配额，需要有管理员权限
        """
        return handlers.VmServiceHandler.change_private_quota(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务私有配额'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @private_quota.mapping.get
    def get_private_quota(self, request, *args, **kwargs):
        """
        查询服务私有配额，需要有管理员权限

            http code 200 ok:
            {
              "private_ip_total": 10,
              "public_ip_total": 8,
              "vcpu_total": 20,
              "ram_total": 10240,       # Mb
              "disk_size_total": 0,     # GB
              "private_ip_used": 5,
              "public_ip_used": 0,
              "vcpu_used": 6,
              "ram_used": 6144,         # Mb
              "disk_size_used": 0,      # GB
              "creation_time": null,
              "enable": true
            }
        """
        return handlers.VmServiceHandler.get_private_quota(
            view=self, request=request, kwargs=kwargs)

    @action(methods=[], detail=True, url_path='s-quota', url_name='share-quota')
    def share_quota(self, request, *args, **kwargs):
        pass

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务共享配额'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @share_quota.mapping.get
    def get_share_quota(self, request, *args, **kwargs):
        """
        查询服务共享配额，需要有管理员权限

            http code 200 ok:
            {
              "private_ip_total": 10,
              "public_ip_total": 8,
              "vcpu_total": 20,
              "ram_total": 10240,       # Mb
              "disk_size_total": 0,     # GB
              "private_ip_used": 5,
              "public_ip_used": 0,
              "vcpu_used": 6,
              "ram_used": 6144,         # Mb
              "disk_size_used": 0,      # GB
              "creation_time": null,
              "enable": true
            }
        """
        return handlers.VmServiceHandler.get_share_quota(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改服务共享配额'),

        responses={
            status.HTTP_200_OK: ''
        }
    )
    @share_quota.mapping.post
    def change_share_quota(self, request, *args, **kwargs):
        """
        修改服务共享配额，需要有管理员权限

            http code 200 ok:
            {
              "private_ip_total": 10,
              "public_ip_total": 8,
              "vcpu_total": 20,
              "ram_total": 10240,       # Mb
              "disk_size_total": 0,     # GB
              "private_ip_used": 5,
              "public_ip_used": 0,
              "vcpu_used": 6,
              "ram_used": 6144,         # Mb
              "disk_size_used": 0,      # GB
              "creation_time": null,
              "enable": true
            }
        """
        return handlers.VmServiceHandler.change_share_quota(
            view=self, request=request, kwargs=kwargs)

    def paginate_service_response(self, request, qs):
        paginator = self.paginator
        try:
            quotas = paginator.paginate_queryset(request=request, queryset=qs)
            serializer = serializers.ServiceSerializer(quotas, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

        return response

    def get_serializer_class(self):
        if self.action == 'change_private_quota':
            return serializers.VmServicePrivateQuotaUpdateSerializer
        elif self.action == 'change_share_quota':
            return serializers.VmServiceShareQuotaUpdateSerializer

        return Serializer

    @property
    def paginator(self):
        if self.action in ['get_share_quota', 'get_private_quota']:
            return None

        return super().paginator


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
                  "name_en": "string",
                  "abbreviation": "xxx"
                  "endpoint_vms": http://xxx/,
                  "endpoint_object": http://xxx/,
                  "endpoint_compute": http://xxx/,
                  "endpoint_monitor": http://xxx/,
                  "creation_time": 2021-02-07T06:20:00Z,
                  "status": {
                    "code": 1,
                    "message": "开启状态"
                  },
                  "desc": "",
                  "longitude": 0,
                  "latitude": 0
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


class ServerArchiveViewSet(CustomGenericViewSet):
    """
    虚拟服务器归档记录相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户虚拟服务器归档记录'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='服务provider id'
            ),
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户个人虚拟服务器归档记录

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
                      "deleted_time": "2021-02-01T08:35:04.154218Z",
                      "classification": "personal",
                      "vo_id": null    # string when "classification"=="vo"
                    }
                  ]
                }
        """
        return ServerArchiveHandler.list_archives(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举vo组的服务器归档记录'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='服务provider id'
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='vo/(?P<vo_id>.+)', url_name='list-vo-archives')
    def list_vo_archives(self, request, *args, **kwargs):
        return ServerArchiveHandler.list_vo_archives(
            view=self, request=request, kwargs=kwargs)


class UserViewSet(CustomGenericViewSet):
    """
    用户视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('获取用户个人信息'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='account', url_name='account')
    def account(self, request, *args, **kwargs):
        """
        获取用户个人信息

            Http Code: 状态码200，返回数据：
            {
              "id": "c172f4b8-984d-11eb-b920-90b11c06b9df",
              "username": "admin",
              "fullname": "",
              "role": {
                "role": [
                  "ordinary", "vms-admin", "storage-admin", "federal-admin"
                ]
              }
            }

        """
        serializer = serializers.UserSerializer(instance=request.user)
        return Response(data=serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('获取用户角色和权限策略信息'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='permission-policy', url_name='permission-policy')
    def permission_policy(self, request, *args, **kwargs):
        """
        获取用户角色和权限策略信息

            200 ok:
            {
              "role": "federal-admin",      # 'ordinary': 普通用户；'federal-admin': 联邦管理员
              "vms": {                      # 有管理员权限的接入服务id
                "role": "admin",
                "service_ids": [
                  "2"
                ]
              }
            }
        """
        user = request.user
        qs = ServiceManager().get_has_perm_service(user)
        service_ids = list(qs.values_list('id', flat=True))
        role = user.Roles.ORDINARY.value
        if user.is_federal_admin():
            role = user.Roles.FEDERAL.value
        data = {
            'role': role,
            'vms': {
                'role': 'admin',
                'service_ids': service_ids
            }
        }
        return Response(data=data)


class ApplyOrganizationViewSet(CustomGenericViewSet):
    """
    机构/数据中心申请视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    list_manual_parameters = [
        openapi.Parameter(
            name='deleted',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_BOOLEAN,
            description=gettext_lazy('筛选参数，true(只返回已删除的申请记录)；false(不包含已删除的申请记录)')
        ),
        openapi.Parameter(
            name='status',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_STRING,
            enum=ApplyOrganization.Status.values,
            description=gettext_lazy('筛选参数，筛选指定状态的申请记录')
        )
    ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举机构申请'),
        manual_parameters=list_manual_parameters,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举机构申请

            http code 200 ok:
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "69580ac6-c439-11eb-9c87-c8009fe2eb10",
                  "creation_time": null,
                  "status": "wait",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "deleted": false,
                  "name": "test",
                  "name_en": "string",
                  "abbreviation": "tt",
                  "independent_legal_person": true,
                  "country": "中国",
                  "city": "北京",
                  "postal_code": "274100",
                  "address": "string",
                  "endpoint_vms": "",
                  "endpoint_object": "",
                  "endpoint_compute": "",
                  "endpoint_monitor": "",
                  "desc": "string",
                  "logo_url": "string",
                  "certification_url": "string",
                  "longitude": 0,
                  "latitude": 0
                }
              ]
            }
        """
        return handlers.ApplyOrganizationHandler.list_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员列举机构申请'),
        manual_parameters=list_manual_parameters,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='admin', url_name='admin-list')
    def admin_list(self, request, *args, **kwargs):
        """
        联邦管理员列举机构申请
        """
        return handlers.ApplyOrganizationHandler.admin_list_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('提交机构/数据中心创建申请'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        提交机构/数据中心创建申请

            Http Code: 状态码200，返回数据：
            {
              "id": "be1f706c-c43e-11eb-867e-c8009fe2eb10",
              "creation_time": null,
              "status": "wait",
              "user": {
                "id": "1",
                "username": "shun"
              },
              "deleted": false,
              "name": "中国科学院计算机信息网络中心",
              "name_en": "string",
              "abbreviation": "中科院网络中心",
              "independent_legal_person": true,
              "country": "中国",
              "city": "北京",
              "postal_code": "100083",
              "address": "北京市海淀区",
              "endpoint_vms": "https://vms.cstcloud.cn/",
              "endpoint_object": "",
              "endpoint_compute": "",
              "endpoint_monitor": "",
              "desc": "test",
              "logo_url": "/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg",
              "certification_url": "/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx",
              "longitude": 0,
              "latitude": 0
            }
            补充说明:
            "status" values:
                wait: 待审批              # 允许申请者修改
                cancel: 取消申请        # 只允许申请者取消
                pending: 审批中            # 挂起，不允许申请者修改，只允许管理者审批
                pass: 审批通过
                reject: 拒绝

            http code 400, 401, 403, 404, 409, 500:
            {
              "code": "xxx",            # "TooManyApply",
              "message": "xxx"             # "您已提交了多个申请，待审批，暂不能提交更多的申请"
            }
        """
        return handlers.ApplyOrganizationHandler.create_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除申请'),
        responses={
            status.HTTP_204_NO_CONTENT: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除
        """
        return handlers.ApplyOrganizationHandler.delete_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('操作审批一个申请'),
        request_body=no_body,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='action/(?P<action>.+)', url_name='action')
    def apply_action(self, request, *args, **kwargs):
        """
        操作审批一个申请

            * action命令选项：
                cancel：取消申请
                pending：挂起申请（审核中）
                reject：拒绝
                pass：通过

            http code 200 ok:
                {
                  "id": "e7dc0622-c43e-11eb-9b23-c8009fe2eb10",
                  "creation_time": null,
                  "status": "pending",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "deleted": true,
                  "name": "中国科学院计算机信息网络中心",
                  "name_en": "cnic",
                  "abbreviation": "中科院网络中心",
                  "independent_legal_person": true,
                  "country": "中国",
                  "city": "北京",
                  "postal_code": "100083",
                  "address": "北京市海淀区",
                  "endpoint_vms": "https://vms.cstcloud.cn/",
                  "endpoint_object": "",
                  "endpoint_compute": "",
                  "endpoint_monitor": "",
                  "desc": "test",
                  "logo_url": "/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg",
                  "certification_url": "/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx"
                }
            http code 400, 401, 403, 404, 409, 500:
                {
                  "code": "xxx",                # 错误码
                  "message": "xxx"              # 错误信息
                }
        """
        return handlers.ApplyOrganizationHandler.apply_action(
            view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ApplyOrganizationSerializer

        return Serializer


class ApplyVmServiceViewSet(CustomGenericViewSet):
    """
    云主机服务接入申请视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    list_manual_parameters = [
        openapi.Parameter(
            name='deleted',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_BOOLEAN,
            description=gettext_lazy('筛选参数，true(只返回已删除的申请记录)；false(不包含已删除的申请记录)')
        ),
        openapi.Parameter(
            name='organization',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_STRING,
            description=gettext_lazy('筛选参数，机构id')
        ),
        openapi.Parameter(
            name='status',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(
                type=openapi.TYPE_STRING,
                enum=ApplyVmService.Status.values
            ),
            description=gettext_lazy('筛选参数，筛选指定状态的申请记录')
        )
    ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举云主机服务接入申请'),
        manual_parameters=list_manual_parameters,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举云主机服务接入申请

            http code 200 ok:
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "deec2f54-bf86-11eb-bf23-c8009fe2eb10",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "creation_time": "2021-05-28T07:32:35.153984Z",
                  "approve_time": "2021-05-28T07:32:35.154143Z",
                  "status": "wait",
                  "organization_id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
                  "longitude": 0,
                  "latitude": 0,
                  "name": "string",
                  "name_en": "string",
                  "region": "1",
                  "service_type": "evcloud",
                  "cloud_type": "private",
                  "endpoint_url": "http://159.226.235.3",
                  "api_version": "v3",
                  "username": "string",
                  "password": "string",
                  "project_name": "string",
                  "project_domain_name": "string",
                  "user_domain_name": "string",
                  "need_vpn": true,
                  "vpn_endpoint_url": "string",
                  "vpn_api_version": "string",
                  "vpn_username": "string",
                  "vpn_password": null,
                  "deleted": false,
                  "contact_person": "string",
                  "contact_email": "user@example.com",
                  "contact_telephone": "string",
                  "contact_fixed_phone": "string",
                  "contact_address": "string",
                  "remarks": "string",
                  "logo_url": ""
                }
              ]
            }
        """
        return handlers.ApplyVmServiceHandler.list_apply(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管理员列举云主机服务接入申请'),
        manual_parameters=list_manual_parameters,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='admin', url_name='admin-list')
    def admin_list(self, request, *args, **kwargs):
        """
        联邦管理员列举云主机服务接入申请

            http code 200 ok:

        """
        return handlers.ApplyVmServiceHandler.admin_list_apply(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('提交云主机服务接入申请'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        提交云主机服务接入申请

            Http Code: 状态码200，返回数据：
            {
              "id": "deec2f54-bf86-11eb-bf23-c8009fe2eb10",
              "user": {
                "id": "1",
                "username": "shun"
              },
              "creation_time": "2021-05-28T07:32:35.153984Z",
              "approve_time": "2021-05-28T07:32:35.154143Z",
              "status": "wait",
              "organization_id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
              "center_apply_id": null,
              "longitude": 0,
              "latitude": 0,
              "name": "string",
              "name_en": "string",
              "region": "1",
              "service_type": "evcloud",
              "cloud_type": "private",
              "endpoint_url": "http://159.226.235.3",
              "api_version": "v3",
              "username": "string",
              "password": "#e9xd3xa2x8exd8xd3",
              "project_name": "string",
              "project_domain_name": "string",
              "user_domain_name": "string",
              "need_vpn": true,
              "vpn_endpoint_url": "string",
              "vpn_api_version": "string",
              "vpn_username": "string",
              "vpn_password": "string",
              "deleted": false,
              "contact_person": "string",
              "contact_email": "user@example.com",
              "contact_telephone": "string",
              "contact_fixed_phone": "string",
              "contact_address": "string",
              "remarks": "string"
            }
            补充说明:
            "status" values:
                wait: 待审批              # 允许申请者修改
                cancel: 取消申请        # 只允许申请者取消
                pending: 审批中            # 挂起，不允许申请者修改，只允许管理者审批
                first_pass: 初审通过
                first_reject: 初审拒绝
                test_failed: 测试未通过
                test_pass: 测试通过
                pass: 审批通过
                reject: 拒绝
        """
        return handlers.ApplyVmServiceHandler.create_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('操作审批一个申请'),
        request_body=no_body,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='action/(?P<action>.+)', url_name='action')
    def apply_action(self, request, *args, **kwargs):
        """
        操作审批一个申请

            * action命令选项：
                cancel：取消申请
                pending：挂起申请（审核中）
                first_pass：初审通过
                first_reject：初审拒绝
                test：测试
                reject：拒绝
                pass：通过

            http code 200 ok (test命令除外) response A:
            {
                'id': '9417080a-c7fb-11eb-8525-c8009fe2eb10',
                'user': {'id': '94104e5c-c7fb-11eb-8525-c8009fe2eb10', 'username': 'test'},
                'creation_time': '2021-06-08T01:48:10.020838Z',
                'approve_time': '2021-06-08T01:48:10.070267Z',
                'status': 'test_pass',
                'organization_id': '94142dec-c7fb-11eb-8525-c8009fe2eb10',
                'longitude': 0.0,
                'latitude': 0.0,
                'name': '地球大数据',
                "name_en": "string",
                'region': '1',
                'service_type': 'evcloud',
                'endpoint_url': 'http://159.226.235.3/',
                'api_version': 'v3',
                'username': '869588058@qq.com',
                'password': 'wangyushun',
                'project_name': '',
                'project_domain_name': '',
                'user_domain_name': '',
                'need_vpn': True,
                'vpn_endpoint_url': '',
                'vpn_api_version': '',
                'vpn_username': '',
                'vpn_password': '',
                'deleted': False,
                'contact_person': 'shun',
                'contact_email': 'user@example.com',
                'contact_telephone': 'string',
                'contact_fixed_phone': 'string',
                'contact_address': '北京信息化大厦',
                'remarks': 'string',
                'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg'
            }

            * "test" action response B:
            {
                'ok': bool,         # true: 测试通过；false: 测试失败
                'message': '',      # 测试失败描述
                'apply': {
                    参考 response A
                }
            }
        """
        return handlers.ApplyVmServiceHandler.apply_action(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除申请'),
        responses={
            status.HTTP_204_NO_CONTENT: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除
        """
        return handlers.ApplyVmServiceHandler.delete_apply(
            view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ApplyVmServiceCreateSerializer

        return Serializer


class MediaViewSet(CustomGenericViewSet):
    """
    静态文件视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None
    # parser_classes = [parsers.FileUploadParser]
    lookup_field = 'url_path'
    lookup_value_regex = '.+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('上传文件'),
        request_body=openapi.Schema(
            title='二进制数据',
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_BINARY,
        ),
        manual_parameters=[
            openapi.Parameter(
                name='Content-MD5', in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description=gettext_lazy("文件对象hex md5"),
                required=True
            ),
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        上传文件

        * 必须提交标头Content-MD5、Content-Length，将根据提供的MD5值检查对象，如果不匹配，则返回错误。
        * 数据以二进制格式直接填充请求体

        * 上传logo图片，请务必使用logo前缀区分，即url_path = logo/test.png;
        * 机构/组织独立法人单位认证码文件，请务必使用certification前缀区分，即url_path = certification/test.docx;

            http code 200:
            {
                'url_path': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg'     # 上传文件对应的下载路径
            }
        """
        return handlers.MediaHandler.media_upload(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('下载文件'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        下载文件
        """
        return handlers.MediaHandler.media_download(view=self, request=request, kwargs=kwargs)

    def get_parsers(self):
        """
        动态分配请求体解析器
        """
        method = self.request.method.lower()
        act = self.action_map.get(method)
        if act == 'update':
            return [parsers.FileUploadParser()]

        return super().get_parsers()

    def get_permissions(self):
        if self.action in ['retrieve']:
            return []

        return super().get_permissions()


class VOViewSet(CustomGenericViewSet):
    """
    项目组视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举项目组'),
        manual_parameters=[
            openapi.Parameter(
                name='owner',
                type=openapi.TYPE_BOOLEAN,
                in_=openapi.IN_QUERY,
                required=False,
                description=_('列举作为拥有者身份的组，参数不需要值，存在即有效')
            ),
            openapi.Parameter(
                name='member',
                type=openapi.TYPE_BOOLEAN,
                in_=openapi.IN_QUERY,
                required=False,
                description=_('列举作为组员身份的组，参数不需要值，存在即有效')
            )
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户相关的（组员或组拥有者）项目组

            * param "owner", "member"是或的关系，只提交其中一个参数，只列举相关身份的组；
              同时提交时和都不提交效果相同，即列举用户作为组员或组拥有者的项目组；

            http code 200 ok:
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "3bc1b4e8-d232-11eb-8b02-c8009fe2eb10",
                  "name": "test",
                  "company": "string",
                  "description": "test desc",
                  "creation_time": "2021-06-21T01:44:35.774210Z",
                  "owner": {
                    "id": "1",
                    "username": "shun"
                  },
                  "status": "active"
                }
              ]
            }
        """
        return handlers.VoHandler.list_vo(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建项目组'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建项目组

            http code 200 ok:
            {
              "id": "3bc1b4e8-d232-11eb-8b02-c8009fe2eb10",
              "name": "test",
              "company": "string",
              "description": "test desc",
              "creation_time": "2021-06-21T01:44:35.774210Z",
              "owner": {
                "id": "1",
                "username": "shun"
              },
              "status": "active"        # active：正常活动的组； disable：被禁用的组
            }
        """
        return handlers.VoHandler.create(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除项目组'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除项目组

        * 需要先清理组内的资源，如云主机，云硬盘等
        """
        return handlers.VoHandler.delete_vo(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改项目组'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """
        修改项目组

            http code 200:
            {
              "id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
              "name": "string666",
              "company": "cnic",
              "description": "测试",
              "creation_time": "2021-06-21T02:13:16.663967Z",
              "owner": {
                "id": "1",
                "username": "shun"
              },
              "status": "active"
            }
        """
        return handlers.VoHandler.update_vo(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举组员'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=True, url_path='list-members', url_name='vo-list-members')
    def vo_members_list(self, request, *args, **kwargs):
        """
        列举组员

            http code 200:
            {
              "members": [
                {
                  "user": {
                    "id": "15ebb3e4-86cf-11eb-900d-c8009fe2eb10",
                    "username": "wangyushun@cnic.cn"
                  },
                  "role": "member",             # member:普通组员；leader:组管理员
                  "join_time": "2021-06-22T07:40:47.791554Z",
                  "inviter": "shun"
                }
              ],
              "owner": {            # 组拥有者，组长
                "id": "1",
                "username": "shun"
              }
            }
        """
        return handlers.VoHandler.vo_list_members(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('添加组员'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='add-members', url_name='vo-add-members')
    def vo_members_add(self, request, *args, **kwargs):
        """
        添加组员

            * http code 200:
            {
              "success": [          # 添加成功的用户
                {
                  "user": {
                    "id": "15ebb3e4-86cf-11eb-900d-c8009fe2eb10",
                    "username": "wangyushun@cnic.cn"
                  },
                  "role": "member",         # member:普通组员；leader:组管理员
                  "join_time": "2021-06-22T07:40:47.791554Z",
                  "inviter": "shun"
                }
              ],
              "failed": [               # 添加失败的用户
                {
                  "username": "test66",
                  "message": "用户名不存在"   # 添加失败的原因
                }
              ]
            }

            * http code 400, 401, 403, 500:
            {
                "code": "xxx",
                "message": "xxx"
            }
        """
        return handlers.VoHandler.vo_add_members(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('移出组员'),
        responses={
            status.HTTP_204_NO_CONTENT: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='remove-members', url_name='vo-remove-members')
    def vo_members_remove(self, request, *args, **kwargs):
        """
        移出组员
        """
        return handlers.VoHandler.vo_remove_members(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改组成员信息，角色'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='member_id',
                in_=openapi.IN_PATH,
                required=True,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('组员id')
            ),
            openapi.Parameter(
                name='role',
                in_=openapi.IN_PATH,
                required=True,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('组员角色'),
                enum=VoMember.Role.values
            )
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['post'], detail=False, url_path='members/(?P<member_id>.+)/role/(?P<role>.+)',
            url_name='vo-members-role')
    def vo_members_role(self, request, *args, **kwargs):
        """
        修改组成员信息，角色

            http code 200:
            {
              "id": "3b5f3bdc-d3cd-11eb-ab5f-c8009fe2eb10",
              "user": {
                "id": "15ebb3e4-86cf-11eb-900d-c8009fe2eb10",
                "username": "xxx@cnic.cn"
              },
              "role": "leader",
              "join_time": "2021-06-23T02:46:38.283159Z",
              "inviter": "shun"
            }
        """
        return handlers.VoHandler.vo_members_role(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        _action = self.action
        if _action in ['list', 'create']:
            return serializers.VoSerializer
        elif _action == 'partial_update':
            return serializers.VoUpdateSerializer
        elif _action in ['vo_members_add', 'vo_members_remove']:
            return serializers.VoMembersAddSerializer
        elif _action == 'vo_members_list':
            return serializers.VoMemberSerializer

        return Serializer
