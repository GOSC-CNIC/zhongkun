from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from utils.paginators import NoPaginatorInspector
from api.paginations import NewPageNumberPagination
from api.viewsets import NormalGenericViewSet
from ..handlers.ipv4_handlers import IPv4RangeHandler
from ..models import IPv4Range
from ..managers import UserIpamRoleWrapper
from .. import serializers


class IPv4RangeViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举IP地址段'),
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
                description=gettext_lazy('ip查询')
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
                  "page_size": 20,
                  "results": [
                    {
                      "id": "dvpse9qhrxv9acfnmhoavtm0n",
                      "name": "159.226.9.64/26",
                      "status": "assigned", # assigned（已分配），wait(待分配)，reserved（预留）
                      "creation_time": "2021-01-05T23:36:08Z",
                      "update_time": "2021-01-05T23:36:08Z",
                      "assigned_time": "2021-01-05T23:36:08Z",
                      "admin_remark": "",
                      "remark": "",
                      "start_address": 2130706433,  # ipv4 int
                      "end_address": 2130706466,
                      "mask_len": 26,
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
        return IPv4RangeHandler().list_ipv4_ranges(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('添加IPv4地址段'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        添加IPv4地址段，需要有科技网管理员权限

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
                  "start_address": 2130706433,
                  "end_address": 2130706687,
                  "mask_len": 24,
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
        return IPv4RangeHandler().add_ipv4_range(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改IPv4地址段'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        修改IPv4地址段，需要有科技网管理员权限

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
                  "start_address": 2130706433,
                  "end_address": 2130706687,
                  "mask_len": 24,
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
        return IPv4RangeHandler().update_ipv4_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除IPv4地址段'),
        responses={
            204: ''''''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除IPv4地址段，需要有科技网管理员权限

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
        return IPv4RangeHandler().delete_ipv4_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('按掩码长度拆分IPv4地址段'),
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='split', url_name='split')
    def split_ip_range(self, request, *args, **kwargs):
        """
        按掩码长度拆分IPv4地址段，需要有科技网管理员权限

            * 指定的 拆分的掩码长度（1-31） 要大于 被拆分IP地址段的掩码长度
            * 子网掩码长度与被拆分IP地址段的掩码长度相差不允许超过8，即每次拆分子网数量最多不得超过256个

            http Code 200 Ok:
                {
                    "ip_ranges": [
                      "id": "bz05x5wxa3y0viz1dn6k88hww",    # fake时为空字符串
                      "name": "127.0.0.0/24",
                      "status": "wait",
                      "creation_time": "2023-10-26T08:33:56.047279Z",
                      "update_time": "2023-10-26T08:33:56.047279Z",
                      "assigned_time": null,
                      "admin_remark": "test",
                      "remark": "",
                      "start_address": 2130706433,
                      "end_address": 2130706687,
                      "mask_len": 24,
                      "asn": {
                        "id": 5,
                        "number": 65535
                      },
                      "org_virt_obj": null
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
        return IPv4RangeHandler().split_ipv4_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('子网IPv4地址段合并为一个指定掩码长度的超网地址段'),
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=False, url_path='merge', url_name='merge')
    def merge_ip_ranges(self, request, *args, **kwargs):
        """
        子网IPv4地址段合并为一个指定掩码长度的超网地址段，需要有科技网管理员权限

            * 合并的所有子网地址段的状态必须同为"未分配"，或者同为“预留”
            * 所有子网地址段的状态为“预留”状态时，关联机构二级对象要一致
            * 要合并的超网地址段掩码长度要小于等于所有子网地址段的掩码长度
            * 合并的所有子网地址段的AS编码必须一致
            * 合并的所有子网地址段IP地址必须是连续的
            * 所有子网地址段必须都属于要合并的目标超网
            * 一个子网地址段也可以合并超网地址段

            http Code 200 Ok:
                {
                  "id": "bz05x5wxa3y0viz1dn6k88hww",    # fake时为空字符串
                  "name": "127.0.0.0/24",
                  "status": "wait",
                  "creation_time": "2023-10-26T08:33:56.047279Z",
                  "update_time": "2023-10-26T08:33:56.047279Z",
                  "assigned_time": null,
                  "admin_remark": "test",
                  "remark": "",
                  "start_address": 2130706433,
                  "end_address": 2130706687,
                  "mask_len": 24,
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
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return IPv4RangeHandler().merge_ipv4_ranges(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('收回一个子网IPv4地址段'),
        request_body=no_body,
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='recover', url_name='recover')
    def recover_ip_range(self, request, *args, **kwargs):
        """
        从“已分配”和“预留”状态收回一个子网IPv4地址段，需要有科技网管理员权限

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
                  "start_address": 2130706433,
                  "end_address": 2130706687,
                  "mask_len": 24,
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
        return IPv4RangeHandler().recover_ipv4_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('预留一个子网IPv4地址段'),
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
        从“未分配”状态预留一个子网IPv4地址段，需要有科技网管理员权限

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
                  "start_address": 2130706433,
                  "end_address": 2130706687,
                  "mask_len": 24,
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
        return IPv4RangeHandler().reserve_ipv4_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('分配一个子网IPv4地址段'),
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
        从“未分配”和“预留”状态 分配一个子网IPv4地址段，需要有科技网管理员权限

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
                  "start_address": 2130706433,
                  "end_address": 2130706687,
                  "mask_len": 24,
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
        return IPv4RangeHandler.assign_ipv4_range(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改一个子网IPv4地址段备注信息'),
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
                description=gettext_lazy('管理员备注，需要有科技网管理员权限')
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

        * 参数“remark”，修改分配机构管理人员的备注信息
        * 参数“admin_remark”，修改科技网管理员的备注信息，必须和“as-admin”一起使用
        * 科技网管理员可以同时修改2个备注信息
        """
        return IPv4RangeHandler.change_ipv4_range_remark(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.IPv4RangeSerializer
        elif self.action in ['create', 'update']:
            return serializers.IPv4RangeCreateSerializer
        elif self.action == 'split_ip_range':
            return serializers.IPv4RangeSplitSerializer
        elif self.action == 'merge_ip_ranges':
            return serializers.IPv4RangeMergeSerializer

        return Serializer


class IPAMUserRoleViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询用户ipam中用户角色和权限'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询用户ipam中用户角色和权限

            http Code 200 Ok:
                {
                  "id": "c89od410t7hwsejr11tyv52w9",
                  "is_admin": false,
                  "is_readonly": true,
                  "creation_time": "2023-10-18T06:13:00Z",
                  "update_time": "2023-10-18T06:13:00Z",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "organizations": [
                    {
                      "id": "b75r1144s5ucku15p6shp9zgf",
                      "name": "中国科学院计算机网络信息中心",
                      "name_en": "中国科学院计算机网络信息中心"
                    }
                  ]
                }
        """
        urw = UserIpamRoleWrapper(user=request.user)
        user_role = urw.user_role
        data = serializers.IPAMUserRoleSerializer(instance=user_role).data
        orgs = user_role.organizations.all().values('id', 'name', 'name_en')
        data['organizations'] = orgs
        return Response(data=data)

    def get_serializer_class(self):
        return Serializer
