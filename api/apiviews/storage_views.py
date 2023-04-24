from django.utils.translation import gettext_lazy, gettext as _
from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors
from api.viewsets import StorageGenericViewSet
from api.paginations import DefaultPageNumberPagination
from api.serializers import storage as storage_serializers
from storage.managers import ObjectsServiceManager
from storage.models import ObjectsService, Bucket, BucketArchive
from utils.paginators import NoPaginatorInspector
from utils.time import iso_utc_to_datetime


class ObjectsServiceViewSet(StorageGenericViewSet):
    permission_classes = []
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[^/]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举对象存储服务单元'),
        manual_parameters=[
            openapi.Parameter(
                name='center_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='联邦成员机构id'
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询条件，服务单元服务状态, {ObjectsService.Status.choices}'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举对象存储服务单元，无需身份认证

            http code 200：
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "4fa94896-29a6-11ed-861f-c8009fe2ebbc",
                  "name": "test iharbor",
                  "name_en": "en iharbor",
                  "service_type": "iharbor",
                  "endpoint_url": "http://159.226.235.188:8001",
                  "add_time": "2022-09-01T03:29:39.620469Z",
                  "status": "enable",   # enable：服务中；disable：停止服务；deleted：删除
                  "remarks": "test",
                  "provide_ftp": true,
                  "ftp_domains": ["127.0.0.1", "0.0.0.0"],
                  "longitude": 0,
                  "latitude": 0,
                  "pay_app_service_id": "ss",
                  "sort_weight": 8,
                  "data_center": {
                    "id": "1",
                    "name": "网络中心",
                    "name_en": "cnic",
                    "sort_weight": -1
                  }
                }
              ]
            }
        """
        center_id = request.query_params.get('center_id', None)
        status = request.query_params.get('status', None)

        if status is not None and status not in ObjectsService.Status.values:
            return self.exception_response(
                exc=errors.InvalidArgument(message=_('参数“status”的值无效'), code='InvalidStatus'))

        qs = ObjectsServiceManager.get_service_queryset()
        if center_id:
            qs = qs.filter(data_center_id=center_id)

        if status:
            qs = qs.filter(status=status)

        try:
            services = self.paginate_queryset(queryset=qs)
            serializer = self.get_serializer(services, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'list':
            return storage_serializers.ObjectsServiceSerializer

        return Serializer


class StorageStatisticsViewSet(StorageGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[^/]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询对象存储统计信息'),
        manual_parameters=[
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段起（含），ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段止（不含），ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
        ],
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询对象存储统计信息

            http code 200：
            {
              "current_bucket_count": 3,    # 当前存储桶总数量
              "new_bucket_count": 2,        # 指定时间段内创建的正常使用的桶的数量，不指定时间段时统计全部桶
              "new_bucket_delete_count": 1, # 指定时间段内创建的已删除的桶的数量（创建后删除的），不指定时间段时统计全部删除桶
              "total_storage_size": 11607311,   # 指定时间段内创建的桶（不含删除的桶）的总存储容量，byte，不指定时间段时统计全部桶
              "total_object_count": 3           # 指定时间段内创建的存储桶（不含删除的桶）总对象数量，不指定时间段时统计全部桶
            }
        """
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)

        try:
            if time_start is not None:
                time_start = iso_utc_to_datetime(time_start)
                if time_start is None:
                    raise errors.InvalidArgument(message=_('参数“time_start”的值无效的时间格式'))

            if time_end is not None:
                time_end = iso_utc_to_datetime(time_end)
                if time_end is None:
                    raise errors.InvalidArgument(message=_('参数“time_end”的值无效的时间格式'))

            if time_start and time_end:
                if time_start >= time_end:
                    raise errors.InvalidArgument(message=_('参数“time_start”时间必须超前“time_end”时间'))
        except Exception as exc:
            return self.exception_response(exc)

        lookups = {}
        if time_start:
            lookups['creation_time__gte'] = time_start

        if time_end:
            lookups['creation_time__lte'] = time_end

        try:
            bucket_count = Bucket.objects.count()
            if lookups:
                new_bucket_count = Bucket.objects.filter(**lookups).count()
                new_bucket_delete_count = BucketArchive.objects.filter(**lookups).count()
            else:
                new_bucket_count = bucket_count
                new_bucket_delete_count = BucketArchive.objects.count()

            r = Bucket.objects.filter(**lookups).aggregate(
                total_size=Sum('storage_size'), total_count=Sum('object_count'))

            return Response(data={
                'current_bucket_count': bucket_count,
                'new_bucket_count': new_bucket_count,
                'new_bucket_delete_count': new_bucket_delete_count,
                'total_storage_size': r['total_size'] if r['total_size'] else 0,
                'total_object_count': r['total_count'] if r['total_count'] else 0
            })
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        return Serializer
