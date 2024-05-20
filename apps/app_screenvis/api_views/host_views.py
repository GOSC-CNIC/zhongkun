from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.app_screenvis.managers import HostQueryChoices, MetricQueryManager
from apps.app_screenvis.utils import errors
from apps.app_screenvis.models import MetricMonitorUnit, HostCpuUsage, HostNetflow
from apps.app_screenvis.permissions import ScreenAPIIPPermission
from . import NormalGenericViewSet


class MetricHostViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [ScreenAPIIPPermission]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询主机集群当前实时信息'),
        manual_parameters=[
            openapi.Parameter(
                name='unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('主机指标单元id, 查询指定主机集群')
            ),
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{HostQueryChoices.choices}",
                enum=HostQueryChoices.values
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='query', url_name='query')
    def query(self, request, *args, **kwargs):
        """
        查询主机集群当前实时信息

            Http Code: 状态码200，返回数据格式最外层key-value格式，key是查询指标参数值，value是单个查询指标的数据：
            {
                "monitor": {
                    "id": "2",
                    "name": "SDG ceph",
                    "name_en": "test ceph",
                    "unit_type": "ceph",        # server, ceph, tidb
                    "job_tag": "sdgs-ceph",
                    "creation_time": "2024-03-08T14:48:07+08:00"
                  }
                "up_count": [
                    {"metric": {}, "value": [1712718507, "13"]}
                ],     # 数组，可能为空，单项，多项
                "down": [
                    {
                      "metric": {
                        "__name__": "up",
                        "instance": "10.16.1.10:9100",
                        "job": "aiops_hosts_node_metric"
                      },
                      "value": [1712718507, "0"]
                    }
                ],   # 数组，可能为空，单项，多项
                ...
            }

            http code 404, 409：
            {
              "code": "NotFound",
              "message": "查询的指标单元不存在"
            }
            409: Conflict: 数据中心未配置Metric服务信息，无法查询监控数据
        """
        query = request.query_params.get('query', None)
        unit_id = request.query_params.get('unit_id', None)

        if query is None:
            return self.exception_response(errors.BadRequest(message=_('请指定查询指标')))

        if query not in HostQueryChoices.values:
            return self.exception_response(errors.InvalidArgument(message=_('指定的查询指标的值无效')))

        if unit_id is None:
            return self.exception_response(errors.BadRequest(message=_('请指定监控单元')))

        try:
            unit_id = int(unit_id)
        except ValueError:
            return self.exception_response(errors.InvalidArgument(message=_('指定监控单元id无效')))

        try:
            monitor_unit = self.get_host_metric_unit(unit_id=unit_id)
        except errors.Error as exc:
            return self.exception_response(exc)

        try:
            data = MetricQueryManager().query(tag=query, metric_unit=monitor_unit)
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=data, status=200)

    @staticmethod
    def get_host_metric_unit(unit_id: int) -> MetricMonitorUnit:
        """
        查询host监控单元，并验证权限

        :raises: Error
        """
        unit = MetricMonitorUnit.objects.select_related(
            'data_center').filter(id=unit_id, unit_type=MetricMonitorUnit.UnitType.HOST.value).first()
        if unit is None:
            raise errors.NotFound(message=_('查询的指标单元不存在。'))

        return unit

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询主机单元总CPU使用率时序数据'),
        manual_parameters=[
            openapi.Parameter(
                name='unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('主机指标单元id, 查询指定主机集群')
            ),
            openapi.Parameter(
                name='time',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('从指定时间戳向前查询数据，默认为当前时间')
            ),
            openapi.Parameter(
                name='limit',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('指定查询最大数据量，默认200，范围1-2000')
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='query/cpuusage', url_name='query-cpuusage')
    def query_cpuusage(self, request, *args, **kwargs):
        """
        查询主机单元总CPU使用率时序数据

            Http Code 200:
            {
                "results": {
                    {
                        "id": "dghrt34ehewwfdw",
                        "timestamp": 1446758567,
                        "value": 12.3456,   # 0 - 100
                        "unit_id": 1
                      }
                ]
            }
        """
        unit_id = request.query_params.get('unit_id', None)
        timestamp = request.query_params.get('time', None)
        limit = request.query_params.get('limit', None)

        if unit_id:
            try:
                unit_id = int(unit_id)
            except ValueError:
                return self.exception_response(errors.InvalidArgument(message=_('指定监控单元id无效')))

        if timestamp:
            try:
                timestamp = int(timestamp)
                if timestamp < 0:
                    raise ValueError('时间戳不能为负数')
            except ValueError:
                return self.exception_response(errors.InvalidArgument(message=_('指定时间戳无效')))

        if limit:
            try:
                limit = int(limit)
                if limit < 1 or limit > 2000:
                    raise ValueError
            except ValueError:
                return self.exception_response(errors.InvalidArgument(message=_('指定查询数据量范围为1-2000')))
        else:
            limit = 200

        try:
            qs = self.filter_cpuusage_qs(unit_id=unit_id, timestamp=timestamp, limit=limit)
            data = []
            for obj in qs:
                data.insert(0, {
                    'id': obj.id, 'timestamp': obj.timestamp, 'value': obj.value, 'unit_id': obj.unit_id
                })
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data={'results': data}, status=200)

    @staticmethod
    def filter_cpuusage_qs(unit_id: int, timestamp: int, limit: int):
        lookups = {'value__gte': 0}
        if unit_id:
            lookups['unit_id'] = unit_id

        if timestamp:
            lookups['timestamp__lte'] = timestamp

        qs = HostCpuUsage.objects.filter(**lookups).order_by('-timestamp')
        return qs[0:limit]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询主机单元网络流量时序数据'),
        manual_parameters=[
            openapi.Parameter(
                name='unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('主机指标单元id, 查询指定主机集群')
            ),
            openapi.Parameter(
                name='time',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('从指定时间戳向前查询数据，默认为当前时间')
            ),
            openapi.Parameter(
                name='limit',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('指定查询最大数据量，默认200，范围1-2000')
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='query/netflow', url_name='query-netflow')
    def query_netflow(self, request, *args, **kwargs):
        """
        查询主机单元网络流量时序数据

            Http Code 200:
            {
                "results": {
                    {
                        "id": "dghrt34ehewwfdw",
                        "timestamp": 1446758567,
                        "flow_in": 2442.3456,   # B/s
                        "flow_out": 5252.654,   # B/s
                        "unit_id": 1
                      }
                ]
            }
        """
        unit_id = request.query_params.get('unit_id', None)
        timestamp = request.query_params.get('time', None)
        limit = request.query_params.get('limit', None)

        if unit_id:
            try:
                unit_id = int(unit_id)
            except ValueError:
                return self.exception_response(errors.InvalidArgument(message=_('指定监控单元id无效')))

        if timestamp:
            try:
                timestamp = int(timestamp)
                if timestamp < 0:
                    raise ValueError('时间戳不能为负数')
            except ValueError:
                return self.exception_response(errors.InvalidArgument(message=_('指定时间戳无效')))

        if limit:
            try:
                limit = int(limit)
                if limit < 1 or limit > 2000:
                    raise ValueError
            except ValueError:
                return self.exception_response(errors.InvalidArgument(message=_('指定查询数据量范围为1-2000')))
        else:
            limit = 200

        try:
            qs = self.filter_netflow_qs(unit_id=unit_id, timestamp=timestamp, limit=limit)
            data = []
            for obj in qs:
                data.insert(0, {
                    'id': obj.id, 'unit_id': obj.unit_id, 'timestamp': obj.timestamp,
                    'flow_in': obj.flow_in, 'flow_out': obj.flow_out
                })
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data={'results': data}, status=200)

    @staticmethod
    def filter_netflow_qs(unit_id: int, timestamp: int, limit: int):
        lookups = {'flow_in__gte': 0, 'flow_out__gte': 0}
        if unit_id:
            lookups['unit_id'] = unit_id

        if timestamp:
            lookups['timestamp__lte'] = timestamp

        qs = HostNetflow.objects.filter(**lookups).order_by('-timestamp')
        return qs[0:limit]

    def get_serializer_class(self):
        return Serializer
