from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from apps.app_screenvis.utils import errors
from apps.app_screenvis.models import (
    DataCenter, ServerService, ServerServiceTimedStats, VPNTimedStats,
    ObjectService, ObjectServiceTimedStats
)
from apps.app_screenvis.tasks import try_stats_service
from apps.app_screenvis.permissions import ScreenAPIIPPermission
from . import NormalGenericViewSet


class ServerServiceViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [ScreenAPIIPPermission]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个数据中心下各云主机服务单元总的统计数据'),
        deprecated=True,
        responses={
            200: ''''''
        }
    )
    @action(methods=['GET'], detail=False, url_path=r'dc/(?P<dc_id>[^/]+)', url_name='dc')
    def dc_server_stats(self, request, *args, **kwargs):
        """
        查询一个数据中心下各服务单元总的统计数据

            http code 200:
            {
              "server_count": 44,       # 云主机数
              "disk_count": 46,         # 云硬盘数
              "ip_count": 136,          # 总ip数
              "ip_used_count": 26,      # 已用IP数
              "mem_size": 44260,        # 总内存GiB
              "mem_used_size": 4460,    # 已用内存GiB
              "cpu_count": 45040,       # cpu总数
              "cpu_used_count": 480     # cpu已用数
            }
        """
        return self.get_server_stats_response()

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询各云主机服务单元总的统计数据'),
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询各云主机服务单元总的统计数据

            http code 200:
            {
              "server_count": 44,       # 云主机数
              "disk_count": 46,         # 云硬盘数
              "ip_count": 136,          # 总ip数
              "ip_used_count": 26,      # 已用IP数
              "mem_size": 44260,        # 总内存GiB
              "mem_used_size": 4460,    # 已用内存GiB
              "cpu_count": 45040,       # cpu总数
              "cpu_used_count": 480     # cpu已用数
            }
        """
        return self.get_server_stats_response()

    @staticmethod
    def get_server_stats_response():
        # 触发统计服务单元数据
        try:
            try_stats_service()
        except Exception as exc:
            pass

        unit_ids = ServerService.objects.filter(
            status__in=[ServerService.Status.ENABLE.value, ServerService.Status.DISABLE.value]
        ).values_list('id', flat=True)

        obj_list = []
        for unit_id in set(unit_ids):
            obj = ServerServiceTimedStats.objects.filter(service_id=unit_id).order_by('-timestamp').first()
            if obj:
                obj_list.append(obj)

        server_count = 0
        disk_count = 0
        ip_count = 0
        ip_used_count = 0
        mem_size = 0
        mem_used_size = 0
        cpu_count = 0
        cpu_used_count = 0
        for obj in obj_list:
            server_count = server_count + obj.server_count
            disk_count = disk_count + obj.disk_count
            ip_count = ip_count + obj.ip_count
            ip_used_count = ip_used_count + obj.ip_used_count
            mem_size = mem_size + obj.mem_size
            mem_used_size = mem_used_size + obj.mem_used_size
            cpu_count = cpu_count + obj.cpu_count
            cpu_used_count = cpu_used_count + obj.cpu_used_count

        return Response(data={
            'server_count': server_count,
            'disk_count': disk_count,
            'ip_count': ip_count,
            'ip_used_count': ip_used_count,
            'mem_size': mem_size,
            'mem_used_size': mem_used_size,
            'cpu_count': cpu_count,
            'cpu_used_count': cpu_used_count
        })

    def get_serializer_class(self):
        return Serializer


class VPNServiceViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [ScreenAPIIPPermission]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个数据中心下各云主机服务单元总的VPN统计数据'),
        responses={
            200: ''''''
        }
    )
    @action(methods=['GET'], detail=False, url_path=r'dc/(?P<dc_id>[^/]+)', url_name='dc')
    def dc_vpn_stats(self, request, *args, **kwargs):
        """
        查询一个数据中心下各云主机服务单元总的VPN统计数据

            http code 200:
            {
              "vpn_online_count": 44,       # 在线数
              "vpn_active_count": 46,       # 有效数
              "vpn_count": 136              # 总数
            }
        """
        # 触发统计服务单元数据
        try:
            try_stats_service()
        except Exception as exc:
            pass

        dc_id = kwargs['dc_id']
        try:
            dc_id = int(dc_id)
        except ValueError:
            return self.exception_response(errors.InvalidArgument(message=_('数据中心ID无效')))

        unit_ids = ServerService.objects.filter(
            data_center_id=dc_id,
            status__in=[ServerService.Status.ENABLE.value, ServerService.Status.DISABLE.value]
        ).values_list('id', flat=True)
        if not unit_ids:
            if not DataCenter.objects.filter(id=dc_id).exists():
                return self.exception_response(errors.TargetNotExist(message=_('数据中心不存在')))

        obj_list = []
        for unit_id in set(unit_ids):
            obj = VPNTimedStats.objects.filter(service_id=unit_id).order_by('-timestamp').first()
            if obj:
                obj_list.append(obj)

        vpn_online_count = 0
        vpn_active_count = 0
        vpn_count = 0
        for obj in obj_list:
            vpn_online_count = vpn_online_count + obj.vpn_online_count
            vpn_active_count = vpn_active_count + obj.vpn_active_count
            vpn_count = vpn_count + obj.vpn_count

        return Response(data={
            'vpn_online_count': vpn_online_count,
            'vpn_active_count': vpn_active_count,
            'vpn_count': vpn_count
        })

    def get_serializer_class(self):
        return Serializer


class ObjectServiceViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [ScreenAPIIPPermission]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个数据中心下各对象存储服务单元总的统计数据'),
        responses={
            200: ''''''
        }
    )
    @action(methods=['GET'], detail=False, url_path=r'dc/(?P<dc_id>[^/]+)', url_name='dc')
    def dc_object_stats(self, request, *args, **kwargs):
        """
        查询一个数据中心下各对象存储服务单元总的统计数据

            http code 200:
            {
              "bucket_count": 44,       # 存储桶数
              "bucket_storage": 46,     # 存储桶总数据量GiB
              "storage_capacity": 44260,# 总存储容量GiB
              "storage_used": 4460,     # 已用存储容量GiB
            }
        """
        # 触发统计服务单元数据
        try:
            try_stats_service()
        except Exception as exc:
            pass

        dc_id = kwargs['dc_id']
        try:
            dc_id = int(dc_id)
        except ValueError:
            return self.exception_response(errors.InvalidArgument(message=_('数据中心ID无效')))

        unit_ids = ObjectService.objects.filter(
            data_center_id=dc_id,
            status__in=[ObjectService.Status.ENABLE.value, ObjectService.Status.DISABLE.value]
        ).values_list('id', flat=True)
        if not unit_ids:
            if not DataCenter.objects.filter(id=dc_id).exists():
                return self.exception_response(errors.TargetNotExist(message=_('数据中心不存在')))

        obj_list = []
        for unit_id in set(unit_ids):
            obj = ObjectServiceTimedStats.objects.filter(service_id=unit_id).order_by('-timestamp').first()
            if obj:
                obj_list.append(obj)

        bucket_count = 0
        bucket_storage = 0
        storage_used = 0
        storage_capacity = 0
        for obj in obj_list:
            bucket_count = bucket_count + obj.bucket_count
            bucket_storage = bucket_storage + obj.bucket_storage
            storage_used = storage_used + obj.storage_used
            storage_capacity = storage_capacity + obj.storage_capacity

        return Response(data={
            'bucket_count': bucket_count,
            'bucket_storage': bucket_storage,
            'storage_used': storage_used,
            'storage_capacity': storage_capacity
        })

    def get_serializer_class(self):
        return Serializer
