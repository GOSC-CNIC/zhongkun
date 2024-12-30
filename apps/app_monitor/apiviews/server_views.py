from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import MonitorPageNumberPagination
from apps.app_monitor.managers import ServerQueryChoices, ServerQueryV2Choices
from apps.app_monitor import serializers as monitor_serializers
from apps.app_monitor.handlers.monitor_server import MonitorServerQueryHandler


class MonitorUnitServerViewSet(CustomGenericViewSet):
    """
    server监控单元视图集
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = MonitorPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举有访问权限的服务器监控单元'),
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
        列举有访问权限的服务器监控单元

            Http Code: 状态码200，返回数据：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "id": "7fd4bd5c-3794-11ec-93e9-c8009fe2eb10",
                  "name": "智能运管云主机服务云主机监控",
                  "name_en": "智能运管云主机服务云主机监控",
                  "job_tag": "AIOPS-vm-node",
                  "creation": "2021-10-28T02:12:28.118004Z",
                  "remark": "",
                  "sort_weight": 10,
                  "grafana_url": "",
                  "dashboard_url": "",
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
                },
              ]
            }
        """
        return MonitorServerQueryHandler().list_server_unit(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return monitor_serializers.MonitorUnitServerSerializer

        return Serializer


class MonitorServerQueryViewSet(CustomGenericViewSet):
    """
    Server监控Query API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务器集群实时信息'),
        manual_parameters=[
            openapi.Parameter(
                name='monitor_unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('服务器监控单元id, 查询指定服务集群')
            ),
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{ServerQueryChoices.choices}",
                enum=ServerQueryChoices.values
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询主机集群当前实时信息

            Http Code: 状态码200，返回数据：
            [
              {
                "value": [              # maybe null
                  1635387288,
                  "198"
                ],
                "monitor": {        # 监控单元
                  "id": "xxx",
                  "name": "大规模对象存储云主机服务物理服务器监控",
                  "name_en": "大规模对象存储云主机服务物理服务器监控",
                  "job_tag": "obs-node",
                  "creation": "2021-10-28T02:09:37.639453Z"
                }
              }
            ]

            * 当“query”参数为 all_together 时，返回数据格式最外层多一层key-value格式，
            key是查询指标参数值，value是单个查询指标的数据（与单独查询一个指标时的响应数据一样）：
            {
                "host_count": [...],
                "cpu_usage": [...],
                ...
            }

            http code 409：
            {
              "code": "NoMonitorJob",
              "message": "没有配置监控"
            }
        """
        return MonitorServerQueryHandler().query(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务器集群实时信息'),
        manual_parameters=[
            openapi.Parameter(
                name='monitor_unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('服务器监控单元id, 查询指定服务集群')
            ),
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{ServerQueryV2Choices.choices}",
                enum=ServerQueryV2Choices.values
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=False, url_path='v2', url_name='query-v2')
    def query_v2(self, request, *args, **kwargs):
        """
        查询主机集群当前实时信息

            Http Code: 状态码200，返回数据格式最外层key-value格式，key是查询指标参数值，value是单个查询指标的数据：
            {
                "monitor": {        # 监控单元
                  "id": "xxx",
                  "name": "云联邦研发测试集群",
                  "name_en": "云联邦研发测试集群",
                  "job_tag": "Fed-ceph",
                  "creation": "2021-09-07T08:33:11.843168Z"
                }
                "host_up": [],     # 数组，可能为空，单项，多项
                "host_down": [],   # 数组，可能为空，单项，多项
                ...
            }

            http code 409：
            {
              "code": "NoMonitorJob",
              "message": "没有配置监控"
            }
        """
        return MonitorServerQueryHandler().query_v2(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        return Serializer
