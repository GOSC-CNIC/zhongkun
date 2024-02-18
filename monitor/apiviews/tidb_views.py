from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer

from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_yasg.utils import no_body

from api.viewsets import CustomGenericViewSet
from api.paginations import MonitorPageNumberPagination
from monitor.managers.tidb import TiDBQueryChoices, TiDBQueryV2Choices
from monitor.handlers.monitor_tidb import MonitorTiDBQueryHandler
from monitor import serializers as monitor_serializers


class MonitorUnitTiDBViewSet(CustomGenericViewSet):
    """
    TiDB监控单元视图集
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = MonitorPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举有访问权限的TiDB监控单元'),
        manual_parameters=[
            openapi.Parameter(
                name='organization_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('监控机构筛选')
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举有访问权限的TiDB监控单元

            Http Code: 状态码200，返回数据：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "id": "1be0db7e-378e-11ec-aa15-c8009fe2eb10",
                  "name": "大规模对象存储TiDB集群",
                  "name_en": "大规模对象存储TiDB集群",
                  "job_tag": "obs-tidb",
                  "creation": "2021-10-28T01:26:43.498367Z",
                  "remark": "test",
                  "sort_weight": 10,                        # 排序值，正序 由小到大
                  "grafana_url": "xxx",
                  "dashboard_url": "xxx",
                  "version": "6.5.3",
                  "org_data_center": {                  # may be null
                    "id": "xxx",
                    "name": "VMware测试中心",
                    "name_en": "xxx",
                    "sort_weight": 8,
                    "organization": {                 # may be null
                        "id": "0e3169d4c8009fe2ebbc",
                        "name": "test",
                        "name_en": "test en",
                        "sort_weight": 6                        # 排序值，正序 由小到大
                    }
                  }
                }
              ]
            }
        """
        return MonitorTiDBQueryHandler().list_tidb_unit(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return monitor_serializers.MonitorUnitTiDBSerializer

        return Serializer


class MonitorTiDBQueryViewSet(CustomGenericViewSet):
    """
    tidb 监控query API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询TiDB集群当前实时信息'),
        manual_parameters=[
            openapi.Parameter(
                name='monitor_unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('TiDB监控单元id, 查询指定TiDB集群')
            ),
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{TiDBQueryChoices.choices}"
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询TiDB集群当前实时信息

            Http Code: 状态码200，返回数据：
            [                           # 数组，可能为空，单项，多项
              {
                "metric": {                 # 此项的数据内容随查询数据类型变化
                  "instance": "10.16.1.26:2379",
                  "type": "storage_capacity"
                },
                "value": [
                  1631004121.496,
                  "0"
                ],
                "monitor": {        # 监控单元
                  "id": "xxx",
                  "name": "云联邦研发测试Ceph集群",
                  "name_en": "云联邦研发测试Ceph集群",
                  "job_tag": "Fed-ceph",
                  "creation": "2021-09-07T08:33:11.843168Z"
                }
              }
            ]

            * 当“query”参数为 all_together 时，返回数据格式最外层多一层key-value格式，
            key是查询指标参数值，value是单个查询指标的数据（与单独查询一个指标时的响应数据一样）：
            {
                "pd_nodes": [],
                "tidb_nodes": [],
                ...
            }

            http code 409：
            {
              "code": "NoMonitorJob",
              "message": "没有配置监控"
            }
        """
        return MonitorTiDBQueryHandler().query(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询TiDB集群当前实时信息'),
        manual_parameters=[
            openapi.Parameter(
                name='monitor_unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('TiDB监控单元id, 查询指定TiDB集群')
            ),
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{TiDBQueryV2Choices.choices}"
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=False, url_path='v2', url_name='query-v2')
    def query_v2(self, request, *args, **kwargs):
        """
        查询TiDB集群当前实时信息

            Http Code: 状态码200，返回数据格式最外层key-value格式，key是查询指标参数值，value是单个查询指标的数据：
            {
                "monitor": {        # 监控单元
                  "id": "xxx",
                  "name": "云联邦研发测试Ceph集群",
                  "name_en": "云联邦研发测试Ceph集群",
                  "job_tag": "Fed-ceph",
                  "creation": "2021-09-07T08:33:11.843168Z"
                }
                "pd_nodes": [],     # 数组，可能为空，单项，多项
                "tidb_nodes": [],   # 数组，可能为空，单项，多项
                ...
            }

            http code 409：
            {
              "code": "NoMonitorJob",
              "message": "没有配置监控"
            }
        """
        return MonitorTiDBQueryHandler().query_v2(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        return Serializer
