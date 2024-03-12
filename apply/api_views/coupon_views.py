from datetime import datetime

from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors
from utils.time import iso_to_datetime
from api.viewsets import NormalGenericViewSet
from api.paginations import NewPageNumberPagination100
from apply import serializers
from apply.models import CouponApply
from apply.managers.coupon import CouponApplyManager


class CouponApplyViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举资源券申请记录'),
        manual_parameters=NormalGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='service_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('服务类型') + f'{CouponApply.ServiceType.choices}'
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('申请状态') + f'{CouponApply.Status.choices}'
            ),
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('起始时间，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ')
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('截止时间，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ')
            ),
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询vo组的申请')
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举资源券申请记录

            Http Code: 状态码200，返回数据：
            {
                "count": 1,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "id": "o783c5q0y0ttbmwmwkq0d2vgi",
                        "service_type": "server",   # server:云主机; storage：对象存储; monitor-site：站点监控; scan：安全扫描
                        "odc": {                    # 数据中心, maybe null
                            "id": "o77ab69z9tsj824todcp9pwji",
                            "name": "odc2",
                            "name_en": "test_en"
                        },
                        "service_id": "service_id2",
                        "service_name": "service_name2",
                        "service_name_en": "service_name_en2",
                        "face_value": "6000.12",                    # 申请券金额
                        "expiration_time": "2023-12-15T00:00:00Z",  # 申请券到期时间
                        "apply_desc": "申请原因说明",
                        "creation_time": "2023-10-09T00:00:00Z",
                        "update_time": "2023-10-09T00:00:00Z",
                        "user_id": "o76e976pt9w6xbgya4c5acc1o",
                        "username": "tom@cnic.cn",
                        "vo_id": "o76gz1xw3tv2hky5nedw35bwy",
                        "vo_name": "test vo",
                        "owner_type": "vo",     # user, vo
                        "status": "pending",
                        "approver": "",         # 审批人
                        "reject_reason": "",    # 审批拒绝时，拒绝原因
                        "approved_amount": "0.00",  # 审批通过的实际资源券金额
                        "coupon_id": ""
                    }
                ]
            }
            * status:
                wait: 待审批
                cancel: 取消
                pending: 审批中    # 防止审批的同时申请人进行修改
                reject: 拒绝      # 拒绝后用户可以修改重新提交
                pass: 通过
        """
        try:
            data = self._list_validate_params(request)
        except errors.Error as exc:
            return self.exception_response(exc)

        user = request.user
        vo_id = data['vo_id']
        try:
            if self.is_as_admin_request(request):
                queryset = CouponApplyManager().admin_filter_apply_qs(
                    service_type=data['service_type'], status=data['status'],
                    start_time=data['time_start'], end_time=data['time_end'],
                    admin_user=user, vo_id=vo_id
                )
            elif vo_id:
                queryset = CouponApplyManager().filter_vo_apply_qs(
                    service_type=data['service_type'], status=data['status'],
                    start_time=data['time_start'], end_time=data['time_end'],
                    user=user, vo_id=vo_id
                )
            else:
                queryset = CouponApplyManager().filter_user_apply_qs(
                    service_type=data['service_type'], status=data['status'],
                    start_time=data['time_start'], end_time=data['time_end'], user_id=user.id
                )

            objs = self.paginate_queryset(queryset)
            serializer = self.get_serializer(instance=objs, many=True)
            return self.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return self.exception_response(exc)

    @staticmethod
    def _list_validate_params(request) -> dict:
        service_type = request.query_params.get('service_type', None)
        status = request.query_params.get('status', None)
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        vo_id = request.query_params.get('vo_id', None)

        if service_type is not None and service_type not in CouponApply.ServiceType.values:
            raise errors.InvalidArgument(message=_('无效的服务类型'))

        if status is not None and status not in CouponApply.Status.values:
            raise errors.InvalidArgument(message=_('无效的申请状态'))

        if time_start is not None:
            time_start = iso_to_datetime(time_start)
            if not isinstance(time_start, datetime):
                raise errors.InvalidArgument(message=_('起始时间格式有误'))

        if time_end is not None:
            time_end = iso_to_datetime(time_end)
            if not isinstance(time_end, datetime):
                raise errors.InvalidArgument(message=_('截止时间格式有误'))

        if time_start and time_end:
            if time_start >= time_end:
                raise errors.InvalidArgument(message=_('起始时间必须小于截止时间'))

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('无效的vo id'))

        return {
            'service_type': service_type,
            'status': status,
            'time_start': time_start,
            'time_end': time_end,
            'vo_id': vo_id
        }

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CouponApplySerializer

        return Serializer
