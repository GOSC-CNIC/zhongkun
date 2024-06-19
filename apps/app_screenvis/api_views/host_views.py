import time

from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.app_screenvis.managers import HostQueryChoices, MetricQueryManager, HostQueryRangeChoices
from apps.app_screenvis.utils import errors
from apps.app_screenvis.models import MetricMonitorUnit, HostNetflow
from apps.app_screenvis.tasks import try_host_netflow
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
        # 触发统计服务单元数据
        try:
            try_host_netflow()
        except Exception as exc:
            pass

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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询主机单元时间段内指标信息'),
        manual_parameters=[
            openapi.Parameter(
                name='unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('主机单元id')
            ),
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{HostQueryRangeChoices.choices}",
                enum=HostQueryRangeChoices.values
            ),
            openapi.Parameter(
                name='start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description=_('查询起始时间点')
            ),
            openapi.Parameter(
                name='end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('查询截止时间点, 默认是当前时间')
            ),
            openapi.Parameter(
                name='step',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('查询步长, 默认为300, 单位为秒')
            )
        ]
    )
    @action(methods=['get'], detail=False, url_path='query/range', url_name='query-range')
    def query_range(self, request, *args, **kwargs):
        """
        查询主机单元时间段内指标信息

            Http Code: 状态码200，返回数据：
            {
              "cpu_usage": [
                {
                  "metric": {"instance": "10.16.1.10:9100"},
                  "values": [
                    [1718178221, "35.35099206403609" ,
                    [1718228221, "33.81190476192542"]
                  ]
                },
                {
                  "metric": {"instance": "10.16.1.11:9100"},
                  "values": [
                    [1718178221, "21.46111111127078"],
                    [1718228221, "17.68511904765749"]
                  ]
                }
              ],
              "monitor": {
                "id": "1",
                "name": "中国科技云-运维大数据-服务器",
                "name_en": "CSTcloud AIOPS Servers",
                "unit_type": "host",
                "job_tag": "aiops_hosts_node_metric",
                "creation_time": "2024-04-10T02:00:38Z"
              }
            }

            http code 409：
            {
              "code": "NoMonitorJob",
              "message": "没有配置监控"
            }
        """
        try:
            unit_id, query, start, end, step = self.validate_query_range_params(request)
            unit = self.get_host_metric_unit(unit_id=unit_id)
        except errors.Error as exc:
            return self.exception_response(exc)

        try:
            data = MetricQueryManager().query_range(
                tag=query, metric_unit=unit, start=start, end=end, step=step)
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=data, status=200)

    @staticmethod
    def validate_query_range_params(request):
        """
        :return:
            (unit_id: int, query: str, start: int, end: int, step: int)

        :raises: Error
        """
        query = request.query_params.get('query', None)
        unit_id = request.query_params.get('unit_id', None)
        start = request.query_params.get('start', None)
        end = request.query_params.get('end', int(time.time()))
        step = request.query_params.get('step', 300)

        if query is None:
            raise errors.BadRequest(message=_('必须指定查询指标'))

        if query not in HostQueryRangeChoices.values:
            raise errors.InvalidArgument(message=_('指定查询指标无效'))

        if unit_id is None:
            raise errors.BadRequest(message=_('必须指定主机单元'))

        try:
            unit_id = int(unit_id)
            if unit_id <= 0:
                raise ValueError
        except ValueError:
            raise errors.InvalidArgument(message=_('必须指定主机单元id无效, 请尝试一个正整数'))

        if start is None:
            raise errors.BadRequest(message=_('参数"start"必须提交'))

        try:
            start = int(start)
            if start <= 0:
                raise ValueError
        except ValueError:
            raise errors.InvalidArgument(message=_('起始时间"start"的值无效, 请尝试一个正整数'))

        try:
            end = int(end)
            if end <= 0:
                raise ValueError
        except ValueError:
            raise errors.InvalidArgument(message=_('截止时间"end"的值无效, 请尝试一个正整数'))

        timestamp_delta = end - start
        if timestamp_delta < 0:
            raise errors.BadRequest(message=_('截止时间必须大于起始时间'))

        try:
            step = int(step)
        except ValueError:
            raise errors.InvalidArgument(message=_('步长"step"的值无效, 请尝试一个正整数'))

        if step <= 0:
            raise errors.InvalidArgument(message=_('不接受零或负查询解析步长, 请尝试一个正整数'))

        resolution = timestamp_delta // step
        if resolution > 11000:
            raise errors.BadRequest(message=_('超过了每个时间序列11000点的最大分辨率。尝试降低查询分辨率（？step=XX）'))

        return unit_id, query, start, end, step

    def get_serializer_class(self):
        return Serializer
