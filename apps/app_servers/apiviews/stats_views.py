from datetime import datetime

from django.db.models import Sum, Count
from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.app_servers.models import Server, ServerArchive, Disk

from core import errors
from utils.time import iso_to_datetime
from utils.paginators import NoPaginatorInspector
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import NewPageNumberPagination100


class StatsViewSet(CustomGenericViewSet):
    """
    统计
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户个人服务器实例，或者以管理员身份列举服务器实例'),
        request_body=no_body,
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'起始时间，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'截止时间，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定存储服务单元')
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=False, url_path='resources', url_name='resources')
    def res_stats(self, request, *args, **kwargs):
        """
        指定时间段内创建的资源统计，联邦管理员权限

            200: {
              "server": {       # 指定时间段内创建，在使用中的
                "ram": 32762,   # 总内存 GiB
                "cpu": 11258,
                "count": 847
              },
              "deleted_server": {   # 指定时间段内创建，已删除的
                "ram": 53857,   # 总内存 GiB
                "cpu": 11133,
                "count": 1241
              },
              "disk": {         # 指定时间段内创建，在使用中的
                "size": 588709, # 总容量，GiB
                "count": 331
              },
              "deleted_disk": { # 指定时间段内创建，已删除的
                "size": 234546, # 总容量，GiB
                "count": 101
              }
            }
        """
        try:
            params = self.res_stats_validate_params(request=request)
        except Exception as exc:
            return self.exception_response(exc=exc)

        if not request.user.is_federal_admin():
            return self.exception_response(
                exc=errors.AccessDenied(message=_('需要联邦管理员权限')))

        time_start = params['time_start']
        time_end = params['time_end']
        service_id = params['service_id']

        lookups = {}
        if time_start:
            lookups['creation_time__gte'] = time_start
        if time_end:
            lookups['creation_time__lte'] = time_end
        if service_id:
            lookups['service_id'] = service_id

        # server
        server_r = Server.objects.filter(
            task_status=Server.TASK_CREATED_OK, **lookups
        ).aggregate(
            total_ram_size=Sum('ram', default=0),
            total_cpu_size=Sum('vcpus', default=0),
            total_server_count=Count('id', distinct=True),
        )
        archive_r = ServerArchive.objects.filter(
            task_status=Server.TASK_CREATED_OK, archive_type=ServerArchive.ArchiveType.ARCHIVE.value, **lookups
        ).aggregate(
            total_ram_size=Sum('ram', default=0),
            total_cpu_size=Sum('vcpus', default=0),
            total_server_count=Count('id', distinct=True),
        )

        # disk
        disk_r = Disk.objects.filter(
            deleted=False, **lookups
        ).aggregate(
            total_size=Sum('size', default=0),
            total_disk_count=Count('id', distinct=True)
        )
        deleted_disk_r = Disk.objects.filter(
            deleted=True, **lookups
        ).aggregate(
            total_size=Sum('size', default=0),
            total_disk_count=Count('id', distinct=True),
        )

        data = {
            'server': {
                'ram': server_r['total_ram_size'],
                'cpu': server_r['total_cpu_size'],
                'count': server_r['total_server_count']
            },
            'deleted_server': {
                'ram': archive_r['total_ram_size'],
                'cpu': archive_r['total_cpu_size'],
                'count': archive_r['total_server_count']
            },
            'disk': {
                'size': disk_r['total_size'],
                'count': disk_r['total_disk_count']
            },
            'deleted_disk': {
                'size': deleted_disk_r['total_size'],
                'count': deleted_disk_r['total_disk_count']
            }
        }

        return Response(data=data)

    @staticmethod
    def res_stats_validate_params(request) -> dict:
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        service_id = request.query_params.get('service_id', None)

        if time_start is not None:
            time_start = iso_to_datetime(time_start)
            if not isinstance(time_start, datetime):
                raise errors.InvalidArgument(message=_('起始日期时间格式无效'))

        if time_end is not None:
            time_end = iso_to_datetime(time_end)
            if not isinstance(time_end, datetime):
                raise errors.InvalidArgument(message=_('截止日期时间格式无效'))

        if time_start and time_end:
            if time_start >= time_end:
                raise errors.InvalidArgument(message=_('截止时间不得超前起始时间'))

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message=_('服务单元ID无效'))

        return {
            'time_start': time_start,
            'time_end': time_end,
            'service_id': service_id
        }

    def get_serializer_class(self):
        return Serializer
