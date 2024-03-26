from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.app_screenvis.managers import TiDBQueryChoices, MetricQueryManager
from apps.app_screenvis.utils import errors
from apps.app_screenvis.models import MetricMonitorUnit
from . import NormalGenericViewSet


class MetricTiDBViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = []
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询TiDB集群当前实时信息'),
        manual_parameters=[
            openapi.Parameter(
                name='unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('TiDB指标单元id, 查询指定TiDB集群')
            ),
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{TiDBQueryChoices.choices}",
                enum=TiDBQueryChoices.values
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='query', url_name='query')
    def query(self, request, *args, **kwargs):
        """
        查询TiDB集群当前实时信息

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
                "connections_count": [],     # 数组，可能为空，单项，多项
                "qps_count ": [],   # 数组，可能为空，单项，多项
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

        if query not in TiDBQueryChoices.values:
            return self.exception_response(errors.InvalidArgument(message=_(f'指定的查询指标的值无效')))

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
            'data_center').filter(id=unit_id, unit_type=MetricMonitorUnit.UnitType.TIDB.value).first()
        if unit is None:
            raise errors.NotFound(message=_('查询的指标单元不存在。'))

        return unit

    def get_serializer_class(self):
        return Serializer
