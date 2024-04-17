import ipaddress

from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors
from apps.api.paginations import NewPageNumberPagination100
from apps.api.viewsets import NormalGenericViewSet
from apps.app_netbox.managers.common import NetBoxUserRoleWrapper
from apps.app_netbox.models import IPv4RangeRecord
from apps.app_netbox.serializers import ipam as ipam_serializers


class IPv4RangeRecordViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举ipv4地址段变更记录'),
        manual_parameters=[
            openapi.Parameter(
                name='record_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'记录类型，{IPv4RangeRecord.RecordType.choices}'
            ),
            openapi.Parameter(
                name='ipv4',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='查询包含ip的地址段的记录'
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举ipv4地址段变更记录，需要有科技网管理员读权限

            http Code 200 Ok:
                {
                    "count": 2,
                    "page_num": 1,
                    "page_size": 100,
                    "results": [
                        {
                            "id": "50b2ehih9bx9buaaqt2r6zcaj",
                            "creation_time": "2023-11-27T08:51:34.646523Z",
                            "record_type": "merge",
                            "start_address": 2667577601,
                            "end_address": 2667578111,
                            "mask_len": 22,
                            "ip_ranges": [      # split，change, merge时有值
                                {
                                    "start": "159.0.1.1",
                                    "end": "159.0.1.255",
                                    "mask": 24
                                },
                                {
                                    "start": "159.0.2.0",
                                    "end": "159.0.2.255",
                                    "mask": 24
                                }
                            ],
                            "remark": "",
                            "user": {
                                "id": "507dci6g0hdzeot1xxmhb7204",
                                "username": "lisi@cnic.cn"
                            },
                            "org_virt_obj": {
                                "id": "5096psao5modfmydzwfuh2upp",
                                "name": "org virt obj2",
                                "creation_time": "2023-11-27T08:51:34.624451Z",
                                "remark": "",
                                "organization": {
                                    "id": "508kc7vt8kqymfww1ww5k03y9",
                                    "name": "test",
                                    "name_en": "test_en"
                                }
                            }
                        }
                    ]
                }
            * record_type in [add，change，delete，split，reserve，recover，assign]时：
                "start_address", "end_address","mask_len"为被操作的IP地址段信息；
                "ip_ranges"为操作后结果IP地址段信息；

            * record_type = merge时：
                "start_address", "end_address","mask_len"为操作后结果IP地址段信息；
                "ip_ranges"为被操作的IP地址段信息；

            Http Code 403:
                {
                    "code": "AccessDenied",
                    "message": "你没有科技网IP管理功能的管理员权限"
                }
        """
        record_type = request.query_params.get('record_type')
        ipv4 = request.query_params.get('ipv4')
        if record_type and record_type not in IPv4RangeRecord.RecordType.values:
            return self.exception_response(
                errors.InvalidArgument(message=_('记录类型无效')))

        if ipv4:
            try:
                ipv4_int = int(ipaddress.IPv4Address(ipv4))
            except ipaddress.AddressValueError:
                return self.exception_response(
                    errors.InvalidArgument(message=_('ip地址无效')))
        else:
            ipv4_int = None

        ur_wrapper = NetBoxUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_readable():
            return self.exception_response(
                errors.AccessDenied(message=_('你没有IP管理功能的管理员权限')))

        try:
            qs = IPv4RangeRecord.objects.select_related('org_virt_obj__organization', 'user').order_by('-creation_time')
            if record_type:
                qs = qs.filter(record_type=record_type)
            if ipv4_int:
                qs = qs.filter(start_address__lte=ipv4_int, end_address__gte=ipv4_int)

            objs = self.paginate_queryset(qs)
            serializer = self.get_serializer(instance=objs, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'list':
            return ipam_serializers.IPv4RangeRecordSerializer

        return Serializer
