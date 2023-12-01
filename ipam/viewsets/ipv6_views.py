from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.paginations import NewPageNumberPagination100
from api.viewsets import NormalGenericViewSet
from ..handlers.ipv6_handlers import IPv6RangeHandler
from ..models import IPv4Range
from .. import serializers


class IPv6RangeViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
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

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.IPv6RangeSerializer
        elif self.action in ['create', 'update']:
            return serializers.IPv6RangeCreateSerializer

        return Serializer
