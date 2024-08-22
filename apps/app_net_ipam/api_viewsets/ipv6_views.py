from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.api.paginations import NewPageNumberPagination100
from apps.api.viewsets import NormalGenericViewSet
from apps.app_net_ipam.handlers.ipv6_handlers import IPv6RangeHandler
from apps.app_net_ipam.models import IPv4Range
from apps.app_net_ipam import serializers as ipam_serializers
from apps.app_net_ipam.permissions import IPamIPRestrictPermission


class IPv6RangeViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, IPamIPRestrictPermission]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举IPv6地址段'),
        manual_parameters=NormalGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='org_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('机构id筛选')
            ),
            openapi.Parameter(
                name='asn',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=gettext_lazy('ASN编码筛选')
            ),
            openapi.Parameter(
                name='ip',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('ipv6查询')
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('关键字查询，搜索名称和备注')
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('管理员参数，状态筛选') + f'{IPv4Range.Status.choices}'
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举IP地址段

            http Code 200 Ok:
                {
                  "count": 136,
                  "page_num": 1,
                  "page_size": 100,
                  "results": [
                    {
                      "id": "dvpse9qhrxv9acfnmhoavtm0n",
                      "name": "	2400:dd01:1010:30::/64",
                      "status": "assigned", # assigned（已分配），wait(待分配)，reserved（预留）
                      "creation_time": "2021-01-05T23:36:08Z",
                      "update_time": "2021-01-05T23:36:08Z",
                      "assigned_time": "2021-01-05T23:36:08Z",
                      "admin_remark": "",
                      "remark": "",
                      "start_address": 2400:dd01:1010:30::,
                      "end_address": 2400:dd01:1010:30:ffff:ffff:ffff:ffff,
                      "prefixlen": 64,
                      "asn": {
                        "id": 2,
                        "number": 7497
                      },
                      "org_virt_obj": {
                        "id": "bpdztm0hi69ix8krgdjo4q10q",
                        "name": "科技云通行证",
                        "creation_time": "2023-10-17T03:15:15.669750Z",
                        "remark": "",
                        "organization": {
                          "id": "b75r1144s5ucku15p6shp9zgf",
                          "name": "中国科学院计算机网络信息中心",
                          "name_en": "中国科学院计算机网络信息中心"
                        }
                      }
                    }
                  ]
                }

            Http Code 400, 403, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你不是组管理员，没有组管理权限

        """
        return IPv6RangeHandler().list_ipv6_ranges(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('添加IPv6地址段'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        添加IPv6地址段，需要有科技网管理员权限

            http Code 200 Ok:
                {
                  "id": "bz05x5wxa3y0viz1dn6k88hww",
                  "name": "127.0.0.0/24",
                  "status": "wait",
                  "creation_time": "2023-10-26T08:33:56.047279Z",
                  "update_time": "2023-10-26T08:33:56.047279Z",
                  "assigned_time": null,
                  "admin_remark": "test",
                  "remark": "",
                  "start_address": 2400:dd01:1010:30::,
                  "end_address": 2400:dd01:1010:30:ffff:ffff:ffff:ffff,
                  "prefixlen": 64,
                  "asn": {
                    "id": 5,
                    "number": 65535
                  },
                  "org_virt_obj": null
                }

            Http Code 400, 403, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return IPv6RangeHandler().add_ipv6_range(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改IPv6地址段'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        修改IPv6地址段，需要有科技网管理员权限

            http Code 200 Ok:
                {
                  "id": "bz05x5wxa3y0viz1dn6k88hww",
                  "name": "127.0.0.0/24",
                  "status": "wait",
                  "creation_time": "2023-10-26T08:33:56.047279Z",
                  "update_time": "2023-10-26T08:33:56.047279Z",
                  "assigned_time": null,
                  "admin_remark": "test",
                  "remark": "",
                  "start_address": 2400:dd01:1010:30::,
                  "end_address": 2400:dd01:1010:30:ffff:ffff:ffff:ffff,
                  "prefixlen": 64,
                  "asn": {
                    "id": 5,
                    "number": 65535
                  },
                  "org_virt_obj": null
                }

            Http Code 400, 403, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return IPv6RangeHandler().update_ipv6_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除IPv6地址段'),
        responses={
            204: ''''''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除IPv6地址段，需要有科技网管理员权限

            http Code 204 Ok: 无返回数据

            Http Code 401, 403, 404, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return IPv6RangeHandler().delete_ipv6_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('收回一个子网IPv6地址段'),
        request_body=no_body,
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='recover', url_name='recover')
    def recover_ip_range(self, request, *args, **kwargs):
        """
        从“已分配”和“预留”状态收回一个子网IPv6地址段，需要有科技网管理员权限

            http Code 200 Ok:
                {
                  "id": "bz05x5wxa3y0viz1dn6k88hww",
                  "name": "127.0.0.0/24",
                  "status": "wait",
                  "creation_time": "2023-10-26T08:33:56.047279Z",
                  "update_time": "2023-10-26T08:33:56.047279Z",
                  "assigned_time": null,
                  "admin_remark": "test",
                  "remark": "",
                  "start_address": 2400:dd01:1010:30::,
                  "end_address": 2400:dd01:1010:30:ffff:ffff:ffff:ffff,
                  "prefixlen": 64,
                  "asn": {
                    "id": 5,
                    "number": 65535
                  },
                  "org_virt_obj": null
                }

            Http Code 401, 403, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return IPv6RangeHandler().recover_ipv6_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('预留一个子网IPv6地址段'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='org_virt_obj_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('预留机构二级对象id')
            )
        ],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='reserve', url_name='reserve')
    def reserve_ip_range(self, request, *args, **kwargs):
        """
        从“未分配”状态预留一个子网IPv6地址段，需要有科技网管理员权限

            http Code 200 Ok:
                {
                  "id": "bz05x5wxa3y0viz1dn6k88hww",
                  "name": "127.0.0.0/24",
                  "status": "wait",
                  "creation_time": "2023-10-26T08:33:56.047279Z",
                  "update_time": "2023-10-26T08:33:56.047279Z",
                  "assigned_time": null,
                  "admin_remark": "test",
                  "remark": "",
                  "start_address": 2400:dd01:1010:30::,
                  "end_address": 2400:dd01:1010:30:ffff:ffff:ffff:ffff,
                  "prefixlen": 64,
                  "asn": {
                    "id": 5,
                    "number": 65535
                  },
                  "org_virt_obj": null
                }

            Http Code 401, 403, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return IPv6RangeHandler().reserve_ipv6_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('分配一个子网IPv6地址段'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='org_virt_obj_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('分配机构二级对象id')
            )
        ],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='assign', url_name='assign')
    def assign_ip_range(self, request, *args, **kwargs):
        """
        从“未分配”和“预留”状态 分配一个子网IPv6地址段，需要有科技网管理员权限

            http Code 200 Ok:
                {
                  "id": "bz05x5wxa3y0viz1dn6k88hww",
                  "name": "2400:dd01:1010:30::/64",
                  "status": "assigned",
                  "creation_time": "2023-10-26T08:33:56.047279Z",
                  "update_time": "2023-10-26T08:33:56.047279Z",
                  "assigned_time": "2024-08-14T08:25:11.201187Z",
                  "admin_remark": "test",
                  "remark": "",
                  "start_address": 2400:dd01:1010:30::,
                  "end_address": 2400:dd01:1010:30:ffff:ffff:ffff:ffff,
                  "prefixlen": 64,
                  "asn": {
                    "id": 5,
                    "number": 65535
                  },
                  "org_virt_obj": {
                    "id": "8guwq0ks9424oevn8wh624m9s",
                    "name": "山东大学",
                    "creation_time": "2023-10-24T06:12:18.137183Z",
                    "remark": "",
                    "organization": {
                      "id": "8gud3z7setw5703dtzhtgz4d7",
                      "name": "山东大学",
                      "name_en": "山东大学"
                    }
                  }
                }
                }

            Http Code 401, 403, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return IPv6RangeHandler.assign_ipv6_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改一个子网IPv6地址段备注信息'),
        request_body=no_body,
        manual_parameters=NormalGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='remark',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('普通备注')
            ),
            openapi.Parameter(
                name='admin_remark',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('管理员备注，需要有IP地址管理员权限')
            ),
        ],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='remark', url_name='remark')
    def change_ip_range_remark(self, request, *args, **kwargs):
        """
        修改一个子网IPv4地址段备注信息

        * 参数“remark”，修改分配机构管理人员的备注信息，限制255字符
        * 参数“admin_remark”，修改管理员的备注信息，必须和“as-admin”一起使用，限制255字符
        * IP地址管理员可以同时修改2个备注信息
        """
        return IPv6RangeHandler.change_ipv6_range_remark(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('按指定拆分方案拆分IPv6地址段'),
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='plan-split', url_name='plan-split')
    def split_ip_range_to_plan(self, request, *args, **kwargs):
        """
        按指定拆分方案拆分IPv6地址段，需要有ip管理员权限

            * 拆分子网数量最多不得超过256个，提交的子网必须按起始地址正序排列，相邻子网ip地址必须是连续的

            http Code 200 Ok:
                {
                    "ip_ranges": [
                    {
                      "name": "cb00:6fff::/32",
                      "status": "wait",
                      "creation_time": "2023-10-26T08:33:56.047279Z",
                      "update_time": "2023-10-26T08:33:56.047279Z",
                      "assigned_time": null,
                      "admin_remark": "test",
                      "remark": "",
                      "start_address": "cb00:6fff::",
                      "end_address": "cb00:6fff:ffff:ffff:ffff:ffff:ffff:ffff",
                      "prefixlen": 32,
                      "asn": {
                        "id": 5,
                        "number": 65535
                      },
                      "org_virt_obj": null
                    },...
                    ]
                }

            Http Code 400, 403, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return IPv6RangeHandler().split_ip_range_to_plan(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询IPv6地址段拆分方案'),
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=False, url_path='plan', url_name='plan')
    def seek_ip_range_split_plan(self, request, *args, **kwargs):
        """
        查询IPv6地址段拆分方案

            code 200:
            {
              "ip_ranges": [
                {
                  "start": "cb00:6000::",
                  "end": "cb00:6fff:ffff:ffff:ffff:ffff:ffff:ffff",
                  "prefix": 20
                },
                {
                  "start": "cb00:7000::",
                  "end": "cb00:7fff:ffff:ffff:ffff:ffff:ffff:ffff",
                  "prefix": 20
                },
                {
                  "start": "cb00:8000::",
                  "end": "cb00:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
                  "prefix": 17
                }
              ]
            }
        """
        return IPv6RangeHandler().seek_ip_range_split_plan(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('子网IPv6地址段合并为一个指定前缀长度的超网地址段'),
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=False, url_path='merge', url_name='merge')
    def merge_ip_ranges(self, request, *args, **kwargs):
        """
        子网IPv6地址段合并为一个指定前缀长度的超网地址段，需要有IP地址管理员权限

            * 合并的所有子网地址段的状态必须同为"未分配"，或者同为“预留”
            * 所有子网地址段的状态为“预留”状态时，关联机构二级对象要一致
            * 要合并的超网地址段前缀长度要小于等于所有子网地址段的掩码长度
            * 合并的所有子网地址段的AS编码必须一致
            * 合并的所有子网地址段IP地址必须是连续的
            * 所有子网地址段必须都属于要合并的目标超网
            * 一个子网地址段也可以合并超网地址段

            http Code 200 Ok:
                {
                  "id": "bz05x5wxa3y0viz1dn6k88hww",    # fake时为空字符串
                  "name": "cb00:6fff::/32",
                  "status": "wait",
                  "creation_time": "2023-10-26T08:33:56.047279Z",
                  "update_time": "2023-10-26T08:33:56.047279Z",
                  "assigned_time": null,
                  "admin_remark": "test",
                  "remark": "",
                  "start_address": "cb00:6fff::",
                  "end_address": "cb00:6fff:ffff:ffff:ffff:ffff:ffff:ffff",
                  "prefixlen": 32,
                  "asn": {
                    "id": 5,
                    "number": 65535
                  },
                  "org_virt_obj": null
                }

            Http Code 400, 403, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你没有IP管理功能的管理员权限
        """
        return IPv6RangeHandler().merge_ipv6_ranges(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return ipam_serializers.IPv6RangeSerializer
        elif self.action in ['create', 'update']:
            return ipam_serializers.IPv6RangeCreateSerializer
        elif self.action == 'split_ip_range_to_plan':
            return ipam_serializers.IPv6RangePlanSplitSerializer
        elif self.action == 'seek_ip_range_split_plan':
            return ipam_serializers.IPv6RangeSpiltPlanPost
        elif self.action == 'merge_ip_ranges':
            return ipam_serializers.IPv6RangeMergeSerializer

        return Serializer
