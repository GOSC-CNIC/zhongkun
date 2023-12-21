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
from servers.managers import ServerManager, DiskManager
from service.models import DataCenter, ApplyOrganization, ApplyVmService
from adapters import inputs, outputs
from core import request as core_request
from core import errors as exceptions
from api.serializers import serializers, disk_serializers
from api.viewsets import CustomGenericViewSet
from api.paginations import ServersPagination, DefaultPageNumberPagination, ImagesPagination
from api.handlers import (
    handlers, ServerHandler, ServerArchiveHandler, VPNHandler,
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
                                  name='public',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_BOOLEAN,
                                  required=False,
                                  description=gettext_lazy('过滤条件，“true”:ip为公网的服务器; "false": ip为私网的服务器')
                              ),
                              openapi.Parameter(
                                  name='remark',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('过滤条件，服务器备注模糊查询')
                              ),
                              openapi.Parameter(
                                  name='status',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('过滤条件') + str(ServerHandler.ListServerQueryStatus.choices)
                              ),
                              openapi.Parameter(
                                  name='user-id',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('过滤条件，用户id，此参数只有以管理员身份请求时有效，否则400，不能与参数“username”一起提交')
                              ),
                              openapi.Parameter(
                                  name='username',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('过滤条件，用户名，此参数只有以管理员身份请求时有效，否则400，不能与参数“user-id”一起提交')
                              ),
                              openapi.Parameter(
                                  name='vo-id',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('过滤条件，vo组id，此参数只有以管理员身份请求时有效，否则400，不能与参数“vo-name”一起提交')
                              ),
                              openapi.Parameter(
                                  name='vo-name',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('过滤条件，vo组名称，此参数只有以管理员身份请求时有效，否则400，不能与参数“vo-id”一起提交')
                              ),
                              openapi.Parameter(
                                  name='exclude-vo',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('过滤条件，排除vo组只查询个人，此参数不需要值，此参数只有以管理员身份请求时有效，否则400，'
                                                           '不能与参数“vo-id”、“vo-name”一起提交')
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
                  "ram": 1, # GiB
                  "ram_gib": 1,
                  "ipv4": "10.0.200.249",
                  "public_ip": false,
                  "image_id": "xx",
                  "image_desc": "xx",
                  "image": "CentOS_9",
                  "img_sys_type": "Linux",
                  "img_sys_arch": "x86-64",
                  "img_release": "CentOS",
                  "img_release_version": "stream 9",
                  "creation_time": "2020-11-02T07:47:39.776384Z",
                  "remarks": "",
                  "service": {
                    "id": "2",
                    "name": "怀柔204机房",
                    "name_en": "xxx",
                    "service_type": "evcloud"
                  },
                  "center_quota": 2,         # 1: 服务的私有资源配额，"user_quota"=null; 2: 服务的分享资源配额
                  "classification": "personal",
                  "vo_id": null,
                  "vo": {           # may be null
                    "id": "1",
                    "name": "测试"
                  },
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
            openapi.Parameter(
                name='expired',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('过滤条件，“true”:查询过期的服务器; "false": 查询未过期的')
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
                  "ram": 1, # GiB
                  "ram_gib": 1,
                  "ipv4": "10.0.200.249",
                  "public_ip": false,
                  "image_id": "xx",
                  "image_desc": "xx",
                  "image": "CentOS_9",
                  "img_sys_type": "Linux",
                  "img_sys_arch": "x86-64",
                  "img_release": "CentOS",
                  "img_release_version": "stream 9",
                  "creation_time": "2020-11-02T07:47:39.776384Z",
                  "remarks": "",
                  "service": {
                    "id": "2",
                    "name": "怀柔204机房",
                    "name_en": "xxx",
                    "service_type": "evcloud"
                  },
                  "center_quota": 2,         # 1: 服务的私有资源配额，"user_quota"=null; 2: 服务的分享资源配额
                  "classification": "vo"
                  "vo_id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",  # 后续移除
                  "vo": {
                    "id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
                    "name": "测试"
                  },
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

            http Code 200 Ok:
                {
                    "order_id": "xxx"
                }

            Http Code 400, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                BadRequest: 请求出现语法错误
                InvalidAzoneId: "azone_id"参数不能为空字符
                MissingPayType: 必须指定付费模式参数"pay_type"
                InvalidPayType: 付费模式参数"pay_type"值无效
                InvalidPeriod: 订购时长参数"period"值必须大于0 / 订购时长最长为5年
                MissingPeriod： 预付费模式时，必须指定订购时长
                InvalidFlavorId: 无效的配置规格flavor id
                InvalidVoId: vo不存在
                MissingServiceId：参数service_id不得为空
                InvalidServiceId：无效的服务id
                InvalidNetworkId: 指定网络不存在
                InvalidAzoneId: 指定的可用区azone_id不存在
                FlavorServiceMismatch: 配置规格和服务单元不匹配

                403:
                AccessDenied: 你不是组管理员，没有组管理权限

                409:
                BalanceNotEnough: 余额不足
                QuotaShortage: 指定服务无法提供足够的资源

                500:
                InternalError: xxx
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

            Http Code 200:
                {
                    "order_id": "xxx",      # 订单id
                }

            Http Code 400, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                BadRequest: 请求出现语法错误
                MissingPeriod: 参数“period”不得为空
                InvalidPeriod: 参数“period”的值无效
                InvalidRenewToTime: 参数“renew_to_time”的值无效的时间格式

                409:
                UnknownExpirationTime: 没有过期时间的云服务器无法续费
                InvalidRenewToTime: 指定的续费终止日期必须在云服务器的过期时间之后
                ResourceLocked: 云主机已加锁锁定了一切操作
                RenewPrepostOnly: 只允许包年包月按量计费的云服务器续费
                RenewDeliveredOkOnly: 只允许为创建成功的云服务器续费
                SomeOrderNeetToTrade: 此云服务器存在未完成的订单, 请先完成已有订单后再提交新的订单

        """
        return ServerHandler().renew_server(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改云服务器实例计费付费方式'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='pay_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('实例需要修改的目标计费方式。可选：prepaid(按量转包月)')
            ),
            openapi.Parameter(
                name='period',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('包年包月续费时长（月），按量转包月时必须指定')
            ),
        ],
        responses={
            200: '''    
                        {
                            "order_id": "xxx",      # 订单id
                        }
                    '''
        }
    )
    @action(methods=['POST'], detail=True, url_path='modify/pay-type', url_name='modify-pay-type')
    def modify_server_pay_type(self, request, *args, **kwargs):
        """
        修改云服务器计费付费方式

            * 暂仅支持按量付费转包年包月，请求成功会创建一个待支付的订单，支付订单成功后，会修改云服务器的计费方式和续费

            Http Code 200:
                {
                    "order_id": "xxx",      # 订单id
                }

            Http Code 400, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                BadRequest: 请求出现语法错误
                MissingPeriod: 按量付费转包年包月必须指定续费时长
                InvalidPeriod: 指定续费时长无效
                MissingPayType: 必须指定付费方式
                InvalidPayType: 指定付费方式无效

                409:
                Conflict: 只允许为创建成功的云服务器修改计费方式; 云服务器所在服务单元未配置对应的结算系统APP服务id;
                            提供此云服务器资源的服务单元停止服务，不允许修改计费方式;
                            必须是按量计费方式的服务器实例才可以转为包年包月计费方式;
                ResourceLocked: 云主机已加锁锁定了一切操作
                SomeOrderNeetToTrade: 此云服务器存在未完成的订单, 请先完成已有订单后再提交新的订单
        """
        return ServerHandler().modify_server_pay_type(view=self, request=request, kwargs=kwargs)

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
                "ram": 1,       # GiB
                "ram_gib": 1,
                "ipv4": "10.0.201.2",
                "public_ip": false,
                "image_id": "xx",
                "image_desc": "xx",
                "image": "CentOS_9",
                "img_sys_type": "Linux",
                "img_sys_arch": "x86-64",
                "img_release": "CentOS",
                "img_release_version": "stream 9",
                "creation_time": "2020-09-23T07:10:14.009418Z",
                "remarks": "",
                "endpoint_url": "",     # 后续移除
                "service": {
                    "id": "2",
                    "name": "怀柔204机房",
                    "name_en": "xxx",
                    "service_type": "evcloud"
                },
                "center_quota": 2,         # 1: 服务的私有资源配额，"user_quota"=null; 2: 服务的分享资源配额
                "classification": "vo",
                "vo_id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",    # null when "classification"=="personal"
                "user": {
                    "id": "1",
                    "username": "shun"
                },
                "lock": "free",    # 'free': 无锁；'lock-delete': 锁定删除，防止删除；'lock-operation', '锁定所有操作，只允许读'
                "attached_disks": [
                  {
                    "id": "dsi1z97pf77644wc1h2m9ry6v-d",
                    "size": 1,
                    "creation_time": "2023-06-26T03:07:26.192272Z",
                    "remarks": "test",
                    "expiration_time": null,
                    "pay_type": "postpaid",
                    "mountpoint": "/dev/vdb",
                    "attached_time": "2023-06-26T06:35:46.280814Z",
                    "detached_time": "2023-06-26T06:30:35.497287Z"
                  }
                ]
              }
            }
        """
        server_id = kwargs.get(self.lookup_field, '')

        try:
            if self.is_as_admin_request(request=request):
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=request.user, related_fields=['service__org_data_center'],
                    as_admin=True)
            else:
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=request.user, related_fields=['service__org_data_center', 'vo__owner'])
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        # 挂载的云硬盘
        disks = DiskManager.get_server_disks_qs(server_id=server.id)
        disk_slz = disk_serializers.ServerDiskSerializer(instance=disks, many=True)
        disks_data = disk_slz.data

        # 如果元数据完整，各种服务不同概率去更新元数据
        need_update = False
        if server.ipv4 and server.image and server.img_sys_type:
            if server.service.service_type == server.service.ServiceType.EVCLOUD:
                if random.choice(range(10)) == 0:
                    need_update = True
            elif server.service.service_type == server.service.ServiceType.OPENSTACK:
                if random.choice(range(5)) == 0:
                    need_update = True
            elif random.choice(range(2)) == 0:
                need_update = True

        if need_update:
            self._update_server_detail(server=server)

        serializer = serializers.ServerSerializer(server)
        data = {'server': serializer.data}
        data['server']['attached_disks'] = disks_data
        return Response(data=data)

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
        return ServerHandler().delete_server(view=self, request=request, kwargs=kwargs)

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
        return ServerHandler().server_action(view=self, request=request, kwargs=kwargs)

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

        if status_code in outputs.ServerStatus.normal_values():  # 虚拟服务器状态正常
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
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN,
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
            if self.is_as_admin_request(request=request):
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=request.user, as_admin=True)
            else:
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
                          ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN,
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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员关机挂起欠费、过期的云服务器'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='act',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'{Server.Situation.choices}'
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['post'], url_path='suspend', detail=True, url_name='server-suspend')
    def server_suspend(self, request, *args, **kwargs):
        """
        管理员关机挂起欠费、过期的云服务器

            http code 200:
            {
                "act": "xxx"
            }
        """
        return ServerHandler.server_suspend(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ServerCreateSerializer
        elif self.action == 'rebuild':
            return serializers.ServerRebuildSerializer

        return Serializer


class ImageViewSet(CustomGenericViewSet):
    """
    系统镜像视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = ImagesPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'
    serializer_class = Serializer

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举镜像'),
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
            200: """"""
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举镜像

            200：
            [
              {
                "id": "18",
                "name": "Ubuntu 2004",
                "release": 系统发行版本，取值空间为{"Windows Desktop", "Windows Server", "Ubuntu", "Fedora", "Centos", "Unknown"},
                "version":系统发行编号（64字符内），取值空间为{"win10","win11","2021","2019","2204","2004","36","37","7","8","9","Unknown",....}
                "architecture":系统架构，取值空间为{"x86-64","i386","arm-64","Unknown"}
                "system_type": 系统类型，取值空间为{"Linux",“Windows","Unknown"}
                "creation_time": "0001-01-01T00:00:00Z",
                "desc": "Ubuntu 2004 旧镜像",
                "default_user": "root",
                "default_password": "cnic.cn",
                "min_sys_disk_gb": 200,
                "min_ram_mb": 0
              }
            ]
        """
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        try:
            params = inputs.ListImageInput(region_id=service.region_id, page_num=1, page_size=100,
                                           flavor_id='')
            r = self.request_service(service, method='list_images', params=params)
            serializer = serializers.ImageOldSerializer(r.images, many=True)
            return Response(data=serializer.data)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('分页列举镜像'),
        manual_parameters=[
            openapi.Parameter(
                name='flavor_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='配置ID（针对阿里云，规格与镜像存在依赖关系）'
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务端点id'
            ),
        ],
        responses={
            200: """"""
        }
    )
    @action(methods=['GET'], detail=False, url_path='paginate', url_name='paginate-list')
    def paginate_list(self, request, *args, **kwargs):
        """
        列举镜像

            200：
            {
                "count": 10,
                "page_num": 1,
                "page_size": 20,
                "results":[
                  {
                    "id": "18",
                    "name": "Ubuntu 2004",
                    "release": 系统发行版本，取值空间为{"Windows Desktop", "Windows Server", "Ubuntu", "Fedora", "Centos", "Unknown"},
                    "version":系统发行编号（64字符内），取值空间为{"win10","win11","2021","2019","2204","2004","36","37","7","8","9","Unknown",....}
                    "architecture":系统架构，取值空间为{"x86-64","i386","arm-64","Unknown"}
                    "system_type": 系统类型，取值空间为{"Linux",“Windows","Unknown"}
                    "creation_time": "0001-01-01T00:00:00Z",
                    "desc": "Ubuntu 2004 旧镜像",
                    "default_user": "root",
                    "default_password": "cnic.cn",
                    "min_sys_disk_gb": 200,
                    "min_ram_mb": 0
                  }
                ]
            }
        """
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        try:
            page_num = self.paginator.get_page_number(request, self.paginator)
            page_size = self.paginator.get_page_size(request)
            flavor_id = request.query_params.get('flavor_id', '')
            service_flavor_id = ''
            if flavor_id:
                flavor = Flavor.objects.filter(id=flavor_id).first()
                if flavor:
                    service_flavor_id = flavor.flavor_id

            params = inputs.ListImageInput(region_id=service.region_id, page_num=page_num, page_size=page_size,
                                           flavor_id=service_flavor_id)
            r = self.request_service(service, method='list_images', params=params)

            serializer = serializers.ImageSerializer(r.images, many=True)
            response = self.paginator.get_paginated_response(data=serializer.data, count=r.count,
                                                             page_num=int(page_num), page_size=page_size)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        return response

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询镜像信息'),
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
            200: """"""
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询镜像信息

            200：
            {
                "id": "18",
                "name": "Ubuntu 2004",
                "release": 系统发行版本，取值空间为{"Windows Desktop", "Windows Server", "Ubuntu", "Fedora", "Centos", "Unknown"},
                "version":系统发行编号（64字符内），取值空间为{"win10","win11","2021","2019","2204","2004","36","37","7","8","9","Unknown",....}
                "architecture":系统架构，取值空间为{"x86-64","i386","arm-64","Unknown"}
                "system_type": "Linux",
                "creation_time": "0001-01-01T00:00:00Z",
                "desc": "Ubuntu 2004 旧镜像",
                "default_user": "root",
                "default_password": "cnic.cn",
                "min_sys_disk_gb": 200,
                "min_ram_mb": 0
            }
        """
        image_id = kwargs.get(self.lookup_field)
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.ImageDetailInput(image_id=image_id, region_id=service.region_id)
        try:
            r = self.request_service(service, method='image_detail', params=params)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.ImageSerializer(instance=r.image, many=False)
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
            http code 409, 500:
            {
              "code": "NoResourcesInService",
              "message": "您和您所在的VO组在此服务单元中没有资源可用，不允许创建此服务单元的VPN账户"
            }
            错误码：
                409 NoResourcesInService：您和您所在的VO组在此服务单元中没有资源可用，不允许创建此服务单元的VPN账户
                500 InternalError：xxx
        """
        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        if VPNHandler.is_need_vpn(service_id=service.id, user=request.user):
            method = 'get_vpn_or_create'
        else:
            method = 'get_vpn'

        try:
            r = self.request_vpn_service(service, method=method, username=request.user.username)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.NotFound as exc:
            if method == 'get_vpn':
                exc = exceptions.ConflictError(
                    message=_('您和您所在的VO组在此服务单元中没有资源可用，不允许创建此服务单元的VPN账户'),
                    code='NoResourcesInService'
                )
            return Response(data=exc.err_data(), status=exc.status_code)
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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('激活VPN账户'),
        request_body=no_body,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='active', url_name='active-vpn')
    def active_vpn(self, request, *args, **kwargs):
        """
        激活VPN账户

            Http Code: 200，成功返回数据：
            {}

            Http Code: 400,404,405, 409,500等失败：
            {
                "code": 'xxx',
                "message": "xxx"
            }

            404:
                ServiceNotExist: 服务单元不存在
            405:
                NoSupportVPN: 服务单元未提供VPN服务
            409:
                ServiceStopped: 服务单元停止服务
                NoResourcesInService：您和您所在的VO组在此服务单元中没有资源可用，不允许激活此服务单元的VPN账户
            500:
                InternalError： xxx
        """
        return VPNHandler.active_vpn(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('停用VPN账户'),
        request_body=no_body,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='deactive', url_name='deactive-vpn')
    def deactive_vpn(self, request, *args, **kwargs):
        """
        停用VPN账户

            Http Code: 200，成功返回数据：
            {}

            Http Code: 400,404,405, 409,500等失败：
            {
                "code": 'xxx',
                "message": "xxx"
            }

            404:
                ServiceNotExist: 服务单元不存在
            405:
                NoSupportVPN: 服务单元未提供VPN服务
            409:
                ServiceStopped: 服务单元停止服务
                NoResourcesInService：您和您所在的VO组在此服务单元中没有资源可用，不允许激活此服务单元的VPN账户
            500:
                InternalError： xxx
        """
        return VPNHandler.deactive_vpn(view=self, request=request)

    def get_serializer_class(self):
        return Serializer

    def get_permissions(self):
        if self.action in ['vpn_config', 'vpn_ca']:
            return []

        return super().get_permissions()


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
        },
        deprecated=True
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
                  "creation_time": 2021-02-07T06:20:00Z,
                  "status": {
                    "code": 1,
                    "message": "开启状态"
                  },
                  "desc": "",
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 6                        # 排序值，由小到大
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
                      "ram": 1,     # Gib
                      "ram_gib": 1,
                      "ipv4": "10.0.200.240",
                      "public_ip": false,
                      "image_id": "xx",
                      "image_desc": "xx",
                      "image": "CentOS_9",
                      "img_sys_type": "Linux",
                      "img_sys_arch": "x86-64",
                      "img_release": "CentOS",
                      "img_release_version": "stream 9",
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
