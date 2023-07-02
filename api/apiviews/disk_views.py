from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.serializers import disk_serializers
from api.paginations import NewPageNumberPagination
from api.handlers.disk_handler import DiskHandler
from utils.paginators import NoPaginatorInspector


class DisksViewSet(CustomGenericViewSet):
    """
    云硬盘视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建云硬盘'),
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
        创建云硬盘

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
                InvalidVoId: vo不存在
                MissingServiceId：参数service_id不得为空
                InvalidServiceId：无效的服务id
                InvalidAzoneId: 指定的可用区azone_id不存在

                403:
                AccessDenied: 你不是组管理员，没有组管理权限

                409:
                BalanceNotEnough: 余额不足
                QuotaShortage: 指定服务无法提供足够的资源

                500:
                InternalError: xxx
        """
        return DiskHandler().disk_order_create(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户或vo组云硬盘'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='服务端点id'
            ),
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('vo组id，查询vo组的云硬盘，需要vo组访问权限')
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户或vo组云硬盘

            http Code 200 Ok:
                {
                  "count": 1,
                  "page_num": 1,
                  "page_size": 20,
                  "results": [
                    {
                      "id": "umimm6qi8vpb2uem8qjrgx7io-d",
                      "name": "",
                      "size": 2,
                      "service": {
                        "id": "2",
                        "name": "怀柔204机房研发测试",
                        "name_en": "怀柔204机房研发测试"
                      },
                      "azone_id": "1",
                      "azone_name": "第1组，公网/内网",
                      "creation_time": "2023-06-20T02:27:54.839869Z",
                      "remarks": "shun开发测试",
                      "task_status": "ok",      # 创建状态，ok: 成功；creating：正在创建中；failed：创建失败
                      "expiration_time": null,
                      "pay_type": "postpaid",   # prepaid: 包年包月; postpaid:按量计费
                      "classification": "vo",   # personal：硬盘归属用户个人
                      "user": {                 # 硬盘创建人
                        "id": "1",
                        "username": "shun"
                      },
                      "vo": {
                        "id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
                        "name": "项目组1"
                      },
                      "lock": "free",   # 'free': 无锁；'lock-delete': 锁定删除，防止删除；'lock-operation', '锁定所有操作，只允许读'
                      "deleted": false, # true: 已删除；false: 正常；只有管理员可查询到已删除云硬盘；
                      "server": {# 挂载的云主机，未挂载时为 null
                        "id": "xxx",
                        "ipv4": "xxx",
                        "vcpus": 6,
                        "ram": 8,   # GiB
                        "image": "CentOS9",
                      },
                      "mountpoint": "/dev/vdb",    # 挂载的设备名/挂载点, 未挂载时为空字符串
                      "attached_time": "2023-06-20T02:27:54.839869Z",   # 上次挂载时间
                      "detached_time": null     # 上次卸载时间
                    }
                  ]
                }

            http Code 400, 401, 403, 404:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400: InvalidArgument: 项目组ID无效
                401: AuthenticationFailed, NotAuthenticated: 身份认证失败
                403: AccessDenied: 你不属于此项目组，没有访问权限
                404: NotFound: 项目组不存在

        """
        return DiskHandler().list_disk(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一块云硬盘详情'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一块用户或vo组的云硬盘详情

            http Code 200 Ok:
            {
              "id": "umimm6qi8vpb2uem8qjrgx7io-d",
              "name": "",
              "size": 2,
              "service": {
                "id": "2",
                "name": "怀柔204机房研发测试",
                "name_en": "怀柔204机房研发测试"
              },
              "azone_id": "1",
              "azone_name": "第1组，公网/内网",
              "creation_time": "2023-06-20T02:27:54.839869Z",
              "remarks": "shun开发测试",
              "task_status": "ok",      # 创建状态，ok: 成功；creating：正在创建中；failed：创建失败
              "expiration_time": null,
              "pay_type": "postpaid",   # prepaid: 包年包月; postpaid:按量计费
              "classification": "vo",   # personal：硬盘归属用户个人
              "user": {                 # 硬盘创建人
                "id": "1",
                "username": "shun"
              },
              "vo": {
                "id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
                "name": "项目组1"
              },
              "lock": "free",   # 'free': 无锁；'lock-delete': 锁定删除，防止删除；'lock-operation', '锁定所有操作，只允许读'
              "deleted": false, # true: 已删除；false: 正常；只有管理员可查询到已删除云硬盘；
              "server": {# 挂载的云主机，未挂载时为 null
                "id": "xxx",
                "ipv4": "xxx",
                "vcpus": 6,
                "ram": 8,   # GiB
                "image": "CentOS9",
              },
              "mountpoint": "/dev/vdb",    # 挂载的设备名/挂载点, 未挂载时为空字符串
              "attached_time": "2023-06-20T02:27:54.839869Z",   # 上次挂载时间
              "detached_time": null     # 上次卸载时间
            }

            http Code 401, 403, 404:
                {
                    "code": "AccessDenied",
                    "message": "xxxx"
                }

                可能的错误码：
                401: AuthenticationFailed, NotAuthenticated: 身份认证失败
                403: AccessDenied: 你不属于此项目组，没有访问权限
                404: DiskNotExist: 云硬盘不存在
        """
        return DiskHandler().detail_disk(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除用户或vo组云硬盘'),
        responses={
            200: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除用户或vo组云硬盘

            http Code 204 Ok:

            http Code 401, 403, 404, 409:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                401: AuthenticationFailed, NotAuthenticated: 身份认证失败
                403: AccessDenied: 没有访问权限
                404: DiskNotExist: 云硬盘不存在
                409:
                    DiskAttached: 云硬盘已挂载于云主机，请先卸载后再尝试删除
                    ResourceLocked: 无法删除，云硬盘已加锁锁定了删除

        """
        return DiskHandler().delete_disk(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('挂载云硬盘到云主机'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='server_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('要挂载的目标云主机ID')
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='attach', url_name='attach')
    def attach_disk(self, request, *args, **kwargs):
        """
        挂载云硬盘到云主机

            http Code 204 Ok:

            http Code 401, 403, 404, 409:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                401: AuthenticationFailed, NotAuthenticated: 身份认证失败
                403: AccessDenied: 没有访问权限
                404: DiskNotExist: 云硬盘不存在
                409:
                    DiskAttached: 云硬盘已挂载于云主机
                    ResourceLocked: 云硬盘已加锁锁定了操作
                    ResourcesNotSameOwner: 指定的云主机和硬盘的所有者不一致
                    ResourcesNotInSameService: 指定的云主机和硬盘不在同一服务单元
                    ResourcesNotInSameZone: 指定的云主机和硬盘不在同一可用区

        """
        return DiskHandler().attach_disk(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('从云主机卸载云硬盘'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='server_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('待卸载的云主机ID')
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='detach', url_name='detach')
    def detach_disk(self, request, *args, **kwargs):
        """
        从云主机卸载云硬盘

            http Code 204 Ok:

            http Code 401, 403, 404, 409:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                401: AuthenticationFailed, NotAuthenticated: 身份认证失败
                403: AccessDenied: 没有访问权限
                404: DiskNotExist: 云硬盘不存在
                409:
                    DiskNotAttached: 云硬盘未挂载
                    ResourceLocked: 目标云主机已加锁锁定了操作
                    DiskNotOnServer: 云硬盘没有挂载在指定的云主机上
        """
        return DiskHandler().detach_disk(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('续费云硬盘'),
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
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='renew', url_name='renew-disk')
    def renew_disk(self, request, *args, **kwargs):
        """
        续费包年包月预付费模式云硬盘，请求成功会创建一个待支付的订单，支付订单成功后，会自动延长云硬盘的过期时间

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
                UnknownExpirationTime: 没有过期时间的云硬盘无法续费
                InvalidRenewToTime: 指定的续费终止日期必须在云硬盘的过期时间之后
                ResourceLocked: 云主机已加锁锁定了一切操作
                RenewPrepostOnly: 只允许包年包月按量计费的云硬盘续费
                RenewDeliveredOkOnly: 只允许为创建成功的云硬盘续费
                SomeOrderNeetToTrade: 此云硬盘存在未完成的订单, 请先完成已有订单后再提交新的订单
        """
        return DiskHandler().renew_disk(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改云硬盘备注信息'),
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
            200: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='remark', url_name='disk-remark')
    def disk_remark(self, request, *args, **kwargs):
        """
        修改云硬盘备注信息

            * vo组云主机需要vo组管理员权限

            http code 200:
            {
                "remarks": "xxx"
            }

            http code 400, 403, 404:
            {
                "code": "AccessDenied",
                "message": "xxx"
            }
            400: InvalidArgument: 参数有效
            403: AccessDenied: 没有访问权限
            404: DiskNotExist: 云硬盘不存在
        """
        return DiskHandler.change_disk_remarks(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return disk_serializers.DiskSerializer
        elif self.action == 'create':
            return disk_serializers.DiskCreateSerializer

        return Serializer
