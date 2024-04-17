import datetime

from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors
from apps.api.viewsets import NormalGenericViewSet
from apps.api.paginations import NewPageNumberPagination100
from apps.report import serializers as report_serializers
from apps.report.managers import (
    ArrearServerQueryOrderBy, ArrearServerManager,
    ArrearBucketQueryOrderBy, ArrearBucketManager
)


class ArrearServerViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询欠费的云主机'),
        manual_parameters=[
            openapi.Parameter(
                name='date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('起始年月，格式：YYYY-MM-DD')
            ),
            openapi.Parameter(
                name='date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('截止年月，格式：YYYY-MM-DD')
            ),
            openapi.Parameter(
                name='order_by',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'排序方式，默认按创建时间降序，{ArrearServerQueryOrderBy.choices}'
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='查询指定服务单元'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询欠费的云主机，以联邦管理员身份查询所有的

            * 欠费云主机记录只代表 记录创建时那个时间点是欠费的状态，不代表当前任然欠费

            http code 200：
            {
                "count": 1,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "id": "2yvts24nrg8j34nxyqi0an8cd",
                        "server_id": "server_id1",
                        "service_id": "2yuh3zw6dusts7qqk3z35sd5y",
                        "service_name": "test",
                        "ipv4": "10.1.1.1",
                        "vcpus": 4,
                        "ram": 4,
                        "image": "CentOS8",
                        "pay_type": "postpaid",
                        "server_creation": "2023-10-18T03:07:54.909804Z",
                        "server_expire": null,
                        "remarks": "test",
                        "user_id": "2yuz9yg8xtehi57syvt405i03",
                        "username": "lilei@xx.com",
                        "vo_id": "",
                        "vo_name": "",
                        "owner_type": "user",
                        "balance_amount": "-121.11",    # 判定为欠费的时间时的 余额
                        "date": "2024-01-16",
                        "creation_time": "2024-01-26T03:07:54.912513Z"  # 判定为欠费的时间
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
                    AccessDenied: 你不是管理员
        """
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        order_by = request.query_params.get('order_by', None)
        service_id = request.query_params.get('service_id', None)

        try:
            if date_start is not None:
                try:
                    date_start = datetime.date.fromisoformat(date_start)
                except (TypeError, ValueError):
                    raise errors.InvalidArgument(message=_('起始日期格式无效'))

            if date_end is not None:
                try:
                    date_end = datetime.date.fromisoformat(date_end)
                except (TypeError, ValueError):
                    raise errors.InvalidArgument(message=_('截止日期格式无效'))

            if date_start and date_end:
                if date_start > date_end:
                    raise errors.InvalidArgument(message=_('起始日期不能在截止日期之前'))

            if order_by is not None:
                if order_by not in ArrearServerQueryOrderBy.values:
                    raise errors.InvalidArgument(message=_('指定的排序方式无效'), code='InvalidOrderBy')
            else:
                order_by = ArrearServerQueryOrderBy.CREATION_TIME_DESC.value
        except Exception as exc:
            return self.exception_response(exc)

        user = request.user
        if not user.is_federal_admin():
            return self.exception_response(exc=errors.AccessDenied(message=_('你没有联邦管理员权限')))

        qs = ArrearServerManager.get_arrear_server_qs(
            date_start=date_start, date_end=date_end, order_by=order_by, service_id=service_id
        )

        try:
            services = self.paginate_queryset(queryset=qs)
            serializer = self.get_serializer(services, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'list':
            return report_serializers.ArrearServerSerializer

        return Serializer


class ArrearBucketViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询欠费的存储桶'),
        manual_parameters=[
            openapi.Parameter(
                name='date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('起始年月，格式：YYYY-MM-DD')
            ),
            openapi.Parameter(
                name='date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('截止年月，格式：YYYY-MM-DD')
            ),
            openapi.Parameter(
                name='order_by',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'排序方式，默认按创建时间降序，{ArrearServerQueryOrderBy.choices}'
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='查询指定服务单元'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询欠费的存储桶，以联邦管理员身份查询所有的

            * 欠费存储桶记录只代表 记录创建时那个时间点是欠费的状态，不代表当前任然欠费

            http code 200：
                {
                    "count": 4,
                    "page_num": 2,
                    "page_size": 1,
                    "results": [
                        {
                            "id": "uspdb4nvd70y1s8oj6dt96ykj",
                            "bucket_id": "bucket_id1",
                            "bucket_name": "name-1",
                            "service_id": "uso2s7kcs5306noej1u6g74mj",
                            "service_name": "test",
                            "size_byte": 123,
                            "object_count": 4,
                            "bucket_creation": "2023-10-18T07:39:12.891419Z",
                            "situation": "normal",
                            "situation_time": "2024-01-26T07:39:12.891419Z",
                            "user_id": "usoiqdfh1muqdjhg03yju2sy9",
                            "username": "lilei@xx.com",
                            "balance_amount": "-221.12",
                            "date": "2024-01-26",
                            "creation_time": "2024-01-26T07:39:12.895084Z",
                            "remarks": "test"
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
                    AccessDenied: 你不是管理员
        """
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        order_by = request.query_params.get('order_by', None)
        service_id = request.query_params.get('service_id', None)

        try:
            if date_start is not None:
                try:
                    date_start = datetime.date.fromisoformat(date_start)
                except (TypeError, ValueError):
                    raise errors.InvalidArgument(message=_('起始日期格式无效'))

            if date_end is not None:
                try:
                    date_end = datetime.date.fromisoformat(date_end)
                except (TypeError, ValueError):
                    raise errors.InvalidArgument(message=_('截止日期格式无效'))

            if date_start and date_end:
                if date_start > date_end:
                    raise errors.InvalidArgument(message=_('起始日期不能在截止日期之前'))

            if order_by is not None:
                if order_by not in ArrearBucketQueryOrderBy.values:
                    raise errors.InvalidArgument(message=_('指定的排序方式无效'), code='InvalidOrderBy')
            else:
                order_by = ArrearBucketQueryOrderBy.CREATION_TIME_DESC.value
        except Exception as exc:
            return self.exception_response(exc)

        user = request.user
        if not user.is_federal_admin():
            return self.exception_response(exc=errors.AccessDenied(message=_('你没有联邦管理员权限')))

        qs = ArrearBucketManager.get_arrear_bucket_qs(
            date_start=date_start, date_end=date_end, order_by=order_by, service_id=service_id
        )

        try:
            services = self.paginate_queryset(queryset=qs)
            serializer = self.get_serializer(services, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'list':
            return report_serializers.ArrearBucketSerializer

        return Serializer
