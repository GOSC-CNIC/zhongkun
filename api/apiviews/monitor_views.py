from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.handlers.monitor_ceph import MonitorCephQueryHandler
from api.handlers.monitor_server import MonitorServerQueryHandler
from api.handlers.monitor_video_meeting import MonitorVideoMeetingQueryHandler
from api.handlers.monitor_website import MonitorWebsiteHandler
from api.serializers import monitor as monitor_serializers
from api.paginations import MonitorPageNumberPagination, MonitorWebsiteTaskPagination
from monitor.managers import CephQueryChoices, ServerQueryChoices, VideoMeetingQueryChoices, WebsiteQueryChoices
from utils.paginators import NoPaginatorInspector


class MonitorCephQueryViewSet(CustomGenericViewSet):
    """
    ceph监控query API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询Cpph集群当前实时信息'),
        manual_parameters=[
            openapi.Parameter(
                name='monitor_unit_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('CEPH监控单元id, 查询指定Cpph集群')
            ),
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{CephQueryChoices.choices}"
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询Cpph集群当前实时信息

            Http Code: 状态码200，返回数据：
            [
              {
                "value": [              # maybe null
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

            http code 409：
            {
              "code": "NoMonitorJob",
              "message": "没有配置监控"
            }
        """
        return MonitorCephQueryHandler().query(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询Ceph集群时间段信息'),
        manual_parameters=[
          openapi.Parameter(
            name='monitor_unit_id',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            required=True,
            description=_('CEPH监控单元id，查询指定Ceph集群')
          ),
          openapi.Parameter(
            name='query',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            required=True,
            description=f"{CephQueryChoices.choices}"
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
    @action(methods=['get'], detail=False, url_path='range', url_name='range')
    def range_list(self, request, *args, **kwargs):
        """
        查询Cpph集群范围信息

            Http Code: 状态码200，返回数据：
            [
              {
                "values": [
                  [1631004121, "0"]
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

            http code 409：
            {
              "code": "NoMonitorJob",
              "message": "没有配置监控"
            }
        """
        return MonitorCephQueryHandler().queryrange(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
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
                description=f"{ServerQueryChoices.choices}"
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

            http code 409：
            {
              "code": "NoMonitorJob",
              "message": "没有配置监控"
            }
        """
        return MonitorServerQueryHandler().query(view=self, request=request, kwargs=kwargs)


class MonitorVideoMeetingQueryViewSet(CustomGenericViewSet):
    """
    Video Meeting 监控 Query API
    """

    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询视频会议节点状态'),
        manual_parameters=[
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{VideoMeetingQueryChoices.choices}"
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询视频会议节点实时延迟和在线状态

            Http Code： 状态码200， 返回数据：
            [
              {
                "monitor": {
                  "name": "科技云会节点监控",
                  "name_en": "科技云会节点监控",
                  "job_tag": "videomeeting"
                },
                "value": [
                  {
                    "value": [
                      1637410040.435,
                      "4.50013087"
                    ],
                    "metric": {
                      "name": "空天院",
                      "longitude": 23.5665,
                      "latitude": 45.1231,
                      "ipv4s": [
                        "159.226.38.98",
                        "159.226.38.99"
                      ]
                    }
                  }
                ]
              }
            ]
        """
        return MonitorVideoMeetingQueryHandler().query(view=self, request=request, kwargs=kwargs)


class MonitorUnitCephViewSet(CustomGenericViewSet):
    """
    ceph监控单元视图集
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = MonitorPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举有访问权限的Ceph监控单元'),
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举有访问权限的Ceph监控单元

            Http Code: 状态码200，返回数据：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "id": "1be0db7e-378e-11ec-aa15-c8009fe2eb10",
                  "name": "大规模对象存储Ceph集群",
                  "name_en": "大规模对象存储Ceph集群",
                  "job_tag": "obs-ceph",
                  "creation": "2021-10-28T01:26:43.498367Z",
                  "remark": "test",
                  "sort_weight": 10,
                  "grafana_url": "xxx",
                  "dashboard_url": "xxx"
                }
              ]
            }
        """
        return MonitorCephQueryHandler().list_ceph_unit(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return monitor_serializers.MonitorUnitCephSerializer

        return Serializer


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
                  "dashboard_url": ""
                },
              ]
            }
        """
        return MonitorServerQueryHandler().list_server_unit(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return monitor_serializers.MonitorUnitServerSerializer

        return Serializer


class MonitorWebsiteViewSet(CustomGenericViewSet):
    """
    站点监控任务
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = MonitorPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建一个站点监控任务'),
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建一个站点监控任务

            Http Code: 状态码200，返回数据：
            {
              "id": "7fd4bd5c-3794-11ec-93e9-c8009fe2eb10",
              "name": "testdev",
              "url": "https://xxx.com",
              "remark": "string",
              "url_hash": "232c139d4ddfce0b1e94ae8a1aea85dd9547a060",
              "creation": "2023-01-13T09:29:32.543642Z"
            }
        """
        return MonitorWebsiteHandler().create_website_task(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户站点监控'),
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户站点监控

            Http Code: 状态码200，返回数据：
            {
              "count": 5,
              "page_num": 3,
              "page_size": 2,
              "results": [
                {
                  "id": "727cee5a-9f70-11ed-aba9-c8009fe2ebbc",
                  "name": "name-string",
                  "url": "https://vms.com",
                  "remark": "string",
                  "url_hash": "8bb5f2cff06fa7a4cdc449e66b9d0c0377a19ede",
                  "creation": "2023-01-29T01:01:22.403887Z",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  }
                }
              ]
            }
        """
        return MonitorWebsiteHandler().list_website_task(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除站点监控'),
        manual_parameters=[
        ],
        responses={
            204: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除站点监控

            Http Code: 状态码204, OK

            http code 403, 404：
            {
              "code": "NotFound",
              "message": "指定监控站点不存在"
            }

            * 可能的错误码：
            403:
                AccessDenied: 无权限访问指定监控站点
            404:
                NotFound: 指定监控站点不存在
        """
        return MonitorWebsiteHandler().delete_website_task(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改站点监控任务'),
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        修改站点监控任务

            Http Code: 状态码200, OK:
            {
              "id": "727cee5a-9f70-11ed-aba9-c8009fe2ebbc",
              "name": "string66",
              "url": "https://666.cn",
              "remark": "string788",
              "url_hash": "67e473e075648ca8305e3ceafca60c0efca9abf7",
              "creation": "2023-01-29T01:01:22.403887Z"
            }

            http code 400, 403, 404：
            {
              "code": "NotFound",
              "message": "指定监控站点不存在"
            }

            * 可能的错误码：
            400:
                BadRequest: 请求格式无效
                InvalidUrl: url网址无效
            403:
                AccessDenied: 无权限访问指定监控站点
            404:
                NotFound: 指定监控站点不存在
        """
        return MonitorWebsiteHandler().change_website_task(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询站点的监控数据'),
        manual_parameters=[
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'{WebsiteQueryChoices.choices}'
            )
        ],
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=True, url_path='query', url_name='data-query')
    def data_query(self, request, *args, **kwargs):
        """
        查询站点的监控数据

            Http Code: 状态码200，返回数据：
            [                           # 数组可能为空
                {
                  "metric": {
                    "__name__": "probe_duration_seconds",
                    "group": "web",
                    "instance": "http_status",
                    "job": "http_status",
                    "monitor": "example",
                    "receive_cluster": "webmonitor",
                    "receive_replica": "0",
                    "tenant_id": "default-tenant",
                    "url": "http://www.xtbg.cas.cn"
                  },
                  "values": [
                    [1675923823.556, "0.021883576"],
                    [1675923838.556, "0.018265911"]
                  ]
                }
            ]

            http code 400, 403, 404, 409：
            {
              "code": "Conflict",
              "message": "未配置监控数据查询服务信息"
            }
        """
        return MonitorWebsiteHandler().query_monitor_data(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定时间段内的站点的监控数据'),
        manual_parameters=[
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'{WebsiteQueryChoices.choices}'
            ),
            openapi.Parameter(
                name='start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description=_('查询起始时间戳')
            ),
            openapi.Parameter(
                name='end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('查询截止时间戳, 默认是当前时间')
            ),
            openapi.Parameter(
                name='step',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=_('查询步长, 默认为300, 单位为秒')
            )
        ],
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=True, url_path='query/range', url_name='data-query-range')
    def data_query_range(self, request, *args, **kwargs):
        """
        查询指定时间段内的站点的监控数据

            * 数据量 = ( end - start ) / step ， 最大数据量10000，超出会报错，情根据参数“end”和“start”合理选择参数“step”的值

            Http Code: 状态码200，返回数据：
            [
              {
                "metric": {
                  "__name__": "probe_duration_seconds",
                  "group": "web",
                  "instance": "http_status",
                  "job": "http_status",
                  "monitor": "example",
                  "receive_cluster": "webmonitor",
                  "receive_replica": "0",
                  "tenant_id": "default-tenant",
                  "url": "http://www.xtbg.cas.cn"
                },
                "values": [
                  [1675992095, "0.018773782"],
                  [1675992107, "0.018449363"]
                ]
              }
            ]

            http code 409：
            {
              "code": "Conflict",
              "message": "未配置监控数据查询服务信息"
            }
        """
        return MonitorWebsiteHandler().query_range_monitor_data(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return monitor_serializers.MonitorWebsiteSerializer
        elif self.action == 'list':
            return monitor_serializers.MonitorWebsiteWithUserSerializer

        return Serializer


class MonitorWebsiteTaskViewSet(CustomGenericViewSet):
    """
    站点监控任务
    """
    queryset = []
    permission_classes = []
    pagination_class = MonitorWebsiteTaskPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('监控服务拉取站点监控任务'),
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        监控服务拉取站点监控任务

            Http Code: 状态码200，返回数据：
            {
              "has_next": false,        # true：有下一页，false：无下一页
              "page_size": 2000,        # 默认每页2000条数据，可通过参数“page_size”指定每页数量，最大10000
              "marker": null,           # 当前页标记
              "next_marker": null,      # 下一页标记
              "results": [
                {
                  "url": "http://vms.com",
                  "url_hash": "8bb5f2cff06fa7a4cdc449e66b9d0c0377a19ede",
                  "creation": "2023-01-29T01:01:22.439153Z"
                }
              ]
            }
        """
        return MonitorWebsiteHandler().monitor_list_website_task(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('监控服务拉取站点监控任务'),
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='version', url_name='version')
    def task_version(self, request, *args, **kwargs):
        """
        站点监控任务当前版本号

            Http Code: 状态码200，返回数据：
            {
              "version": 5,
            }
        """
        return MonitorWebsiteHandler().get_website_task_version(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return monitor_serializers.MonitorWebsiteTaskSerializer

        return Serializer
