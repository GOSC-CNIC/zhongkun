from typing import Union

from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_yasg.utils import no_body

from api.viewsets import CustomGenericViewSet
from api.paginations import MonitorPageNumberPagination, MonitorWebsiteTaskPagination
from utils.paginators import NoPaginatorInspector
from service.models import OrgDataCenter
from core import errors
from monitor.managers import (
    CephQueryChoices, ServerQueryChoices, VideoMeetingQueryChoices, WebsiteQueryChoices
)
from monitor.utils import MonitorEmailAddressIPRestrictor
from monitor.models import MonitorJobCeph, MonitorJobTiDB, MonitorJobServer, LogSite
from monitor.handlers.monitor_ceph import MonitorCephQueryHandler
from monitor.handlers.monitor_server import MonitorServerQueryHandler
from monitor.handlers.monitor_video_meeting import MonitorVideoMeetingQueryHandler
from monitor.handlers.monitor_website import MonitorWebsiteHandler, TaskSchemeType
from monitor import serializers as monitor_serializers


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

            * 当“query”参数为 all_together 时，返回数据格式最外层多一层key-value格式，
            key是查询指标参数值，value是单个查询指标的数据（与单独查询一个指标时的响应数据一样）：
            {
                "health_status": [...],
                "osd_in": [...],
                ...
            }

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
                  "sort_weight": 10,                        # 排序值，正序 由小到大
                  "grafana_url": "xxx",
                  "dashboard_url": "xxx",
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


class MonitorWebsiteViewSet(CustomGenericViewSet):
    """
    站点监控任务
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = MonitorPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建一个http或tcp监控任务'),
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建一个http或tcp监控任务

            Http Code: 状态码200，返回数据：
            {
              "id": "7fd4bd5c-3794-11ec-93e9-c8009fe2eb10",
              "name": "testdev",
              "scheme": "https://", # tcp://
              "hostname": "baidu.com:8888",
              "uri": "/string",
              "is_tamper_resistant": false,
              "url": "https://baidu.com:8888/string",
              "remark": "string",
              "url_hash": "232c139d4ddfce0b1e94ae8a1aea85dd9547a060",
              "creation": "2023-01-13T09:29:32.543642Z",
              "modification": "2023-01-29T01:01:00Z",
              "is_attention": true
            }
            http code 400、409:
            {
                "code": "xxx",
                "message": "xxx"
            }
            400：
                BadRequest：
                InvalidScheme：协议无效
                InvalidHostname：域名无效
                InvalidUri：路径无效
            409：
                TargetAlreadyExists：已存在相同的网址
                BalanceNotEnough：你已拥有x个站点监控任务，你的余额不足，不能创建更多的站点监控任务。
        """
        return MonitorWebsiteHandler().create_website_task(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户站点监控'),
        manual_parameters=[
            openapi.Parameter(
                name='scheme',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'协议类型筛选，{TaskSchemeType.values}'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户站点监控和数据中心监控任务

            Http Code: 状态码200，返回数据：
            {
              "count": 5,
              "page_num": 3,
              "page_size": 2,
              "results": [
                {
                  "id": "727cee5a-9f70-11ed-aba9-c8009fe2ebbc",
                  "name": "name-string",
                  "scheme": "https://",
                  "hostname": "baidu.com:8888",
                  "uri": "/string",
                  "is_tamper_resistant": false,     # 是否防篡改
                  "url": "https://baidu.com:8888/string",
                  "remark": "string",
                  "url_hash": "8bb5f2cff06fa7a4cdc449e66b9d0c0377a19ede",
                  "creation": "2023-01-29T01:01:22.403887Z",
                  "modification": "2023-01-29T01:01:00Z",
                  "user": {     # maybe null，关联用户属于用户的监控任务
                    "id": "1",
                    "username": "shun"
                  },
                  "odc": {  # maybe null，关联数据中心属于数据中心的监控任务，为服务单元自动创建的监控任务，只允许读
                    "id": "xx",
                    "name": "xx",
                    "name_en": "xx",
                  }
                  "is_attention": false
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
        operation_summary=gettext_lazy('修改http或tcp监控任务'),
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        修改http或tcp监控任务

            Http Code: 状态码200, OK:
            {
              "id": "727cee5a-9f70-11ed-aba9-c8009fe2ebbc",
              "name": "string66",
              "scheme": "https://",
              "hostname": "666.cn",
              "uri": "/",
              "is_tamper_resistant": false,
              "url": "https://666.cn/",
              "remark": "string788",
              "url_hash": "67e473e075648ca8305e3ceafca60c0efca9abf7",
              "creation": "2023-01-29T01:01:22.403887Z",
              "modification": "2023-01-29T01:01:00Z",
              "is_attention": true
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
        operation_summary=gettext_lazy('查询http或tcp监控任务监控数据'),
        manual_parameters=[
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'{WebsiteQueryChoices.choices}'
            ),
            openapi.Parameter(
                name='detection_point_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('探测点ID，指定从那个探测点查询数据')
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
        查询http或tcp监控任务监控数据

            Http Code: 状态码200，返回数据：
            [                           # 数组可能为空, 可能有多个数据项， 比如查询参数 query = http_duration_seconds
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

            错误码：
            400：
                BadRequest：请求有误，比如缺少参数
                InvalidArgument： 参数值无效
            403：
                AccessDenied：无权限访问此站点监控任务
            404：
                NotFound：站点监控任务不存在
                NoSuchDetectionPoint: 指定的探测点不存在
            409：
                Conflict：网站监控探测点暂未启用；/ 探测点未配置监控数据查询服务信息
        """
        return MonitorWebsiteHandler().query_monitor_data(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定时间段内的http或tcp监控任务的监控数据'),
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
            ),
            openapi.Parameter(
                name='detection_point_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('探测点ID，指定从那个探测点查询数据')
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
        查询指定时间段内的http或tcp监控任务的监控数据

            * 数据量 = ( end - start ) / step ， 最大数据量10000，超出会报错，情根据参数“end”和“start”合理选择参数“step”的值

            Http Code: 状态码200，返回数据：
            [                                   # 数组可能为空, 可能有多个数据项， 比如查询参数 query = http_duration_seconds
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

            错误码：
            400：
                BadRequest：请求有误，比如缺少参数
                InvalidArgument： 参数值无效
            403：
                AccessDenied：无权限访问此站点监控任务
            404：
                NotFound：站点监控任务不存在
                NoSuchDetectionPoint: 指定的探测点不存在
            409：
                Conflict：网站监控探测点暂未启用；/ 探测点未配置监控数据查询服务信息
        """
        return MonitorWebsiteHandler().query_range_monitor_data(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举站点监控探测点'),
        manual_parameters=[
            openapi.Parameter(
                name='enable',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description=gettext_lazy('筛选条件，true(启用状态的)，false(未启用的)')
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='detection-point', url_name='detection-point')
    def list_detection_point(self, request, *args, **kwargs):
        """
        列举站点监控探测点

            Http Code: 状态码200，返回数据：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "id": "e21c643a-bd83-11ed-87e9-c8009fe2ebbc",
                  "name": "test",
                  "name_en": "test en",
                  "creation": "2023-03-08T07:34:00Z",
                  "modification": "2023-03-08T07:34:00Z",
                  "remark": "备注信息",
                  "enable": true
                }
              ]
            }

            http code 400, 403, 404, 409：
            {
              "code": "Conflict",
              "message": "未配置监控数据查询服务信息"
            }
        """
        return MonitorWebsiteHandler().list_website_detection_point(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('站点监控任务特别关注标记'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='action',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('操作参数,只允许选择“标记（mark）”和“取消标记（unmark）”')
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='attention', url_name='mark-attention')
    def mark_attention(self, request, *args, **kwargs):
        """
        站点监控任务特别关注标记

            Http Code: 状态码200, OK:
            {
              "id": "727cee5a-9f70-11ed-aba9-c8009fe2ebbc",
              "name": "string66",
              "scheme": "https://",
              "hostname": "baidu.com:8888",
              "uri": "/string",
              "is_tamper_resistant": false,     # 是否防篡改
              "remark": "string788",
              "url_hash": "67e473e075648ca8305e3ceafca60c0efca9abf7",
              "creation": "2023-01-29T01:01:22.403887Z",
              "modification": "2023-01-29T01:01:00Z",
              "is_attention": true
            }

            http code 400, 403, 404：
            {
              "code": "NotFound",
              "message": "指定监控站点不存在"
            }

            * 可能的错误码：
            400:
                InvalidArgument: 请求格式无效
            403:
                AccessDenied: 无权限访问指定监控站点
            404:
                NotFound: 指定监控站点不存在
        """
        return MonitorWebsiteHandler().website_task_attention_mark(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('个人监控网站网络延迟区间统计'),
        manual_parameters=[
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
                name='detection_point_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=_('探测点ID，指定从那个探测点查询数据，可选，默认全部探测点')
            )
        ],
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='duration/distribution', url_name='duration-distribution')
    def list_duration_distribution(self, request, *args, **kwargs):
        """
        个人http监控网站网络延迟区间统计

            Http Code: 状态码200，返回数据：
            {
                "a1cfc71a-be4f-11ed-b6f8-c800dfc12405": {
                    ">3s": 0,
                    "1s-3s": 0,
                    "600ms-1s": 0,
                    "300ms-600ms": 0,
                    "100ms-300ms": 0,
                    "50ms-100ms": 0,
                    "<50ms": 2
                }
            }

            http code 409：
            {
              "code": "Conflict",
              "message": "未配置监控数据查询服务信息"
            }

            错误码：
            400：
                BadRequest：请求有误，比如缺少参数
                InvalidArgument： 参数值无效
            404：
                NoSuchDetectionPoint: 指定的探测点不存在
            409：
                Conflict：网站监控探测点暂未启用；/ 探测点未配置监控数据查询服务信息
        """
        return MonitorWebsiteHandler().list_duration_distribution(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('个人监控网站状态统计'),
        manual_parameters=[
            openapi.Parameter(
                name='detection_point_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=_('探测点ID，指定从那个探测点查询数据，可选，默认全部探测点')
            )
        ],
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='status/overview', url_name='status-overview')
    def website_status_overview(self, request, *args, **kwargs):
        """
        个人http监控网站状态统计

            Http Code: 状态码200，返回数据：
            {
              "total": 193,
              "invalid": 11,
              "valid": 182,
              "invalid_urls": [
                "https://test.cn"
              ]
            }

            http code 409：
            {
              "code": "Conflict",
              "message": "未配置监控数据查询服务信息"
            }

            错误码：
            400：
                BadRequest：请求有误，比如缺少参数
            404：
                NoSuchDetectionPoint: 指定的探测点不存在
            409：
                Conflict：网站监控探测点暂未启用；/ 探测点未配置监控数据查询服务信息
        """
        return MonitorWebsiteHandler().http_status_overview(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询监控同一个网站的所有用户的邮件地址'),
        manual_parameters=[
            openapi.Parameter(
                name='url_hash',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('监控站点url hash字符串')
            )
        ],
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='user/email', url_name='user-email')
    def get_site_user_emails(self, request, *args, **kwargs):
        """
        查询监控同一个网站的所有用户和数据中心管理员的邮件地址，不需要身份验证，只有指定的ip可访问

            http code 200:
            {
              "url_hash": "cdf73b92194a75d7965330f2b79de787e39d7a2f",
              "results": [
                {
                  "scheme": "https://",
                  "hostname": "service.cstcloud.cn",
                  "uri": "/",
                  "email": "yzhang@cnic.cn"
                }
              ]
            }
        """
        return MonitorWebsiteHandler.get_site_user_emails(view=self, request=request)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'mark_attention']:
            return monitor_serializers.MonitorWebsiteSerializer
        elif self.action == 'list':
            return monitor_serializers.MonitorWebsiteWithUserSerializer
        elif self.action == 'list_detection_point':
            return monitor_serializers.MonitorWebsiteDetectionPointSerializer

        return Serializer

    def get_authenticators(self):
        authenticators = super().get_authenticators()
        method = self.request.method.lower()
        _act = self.action_map.get(method)
        if _act == 'list':
            authenticators.append(BasicAuthentication())

        return authenticators

    def get_permissions(self):
        if self.action == 'get_site_user_emails':
            return []

        return super().get_permissions()


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
                  "url": "https://vms.com",
                  "url_hash": "8bb5f2cff06fa7a4cdc449e66b9d0c0377a19ede",
                  "creation": "2023-01-29T01:01:22.439153Z",
                  "is_tamper_resistant": true
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


class UnitAdminEmailViewSet(CustomGenericViewSet):
    permission_classes = []
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询各监控单元管理员用户的邮件地址'),
        manual_parameters=[
            openapi.Parameter(
                name='tag',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('监控单元标识标签')
            )
        ],
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询各监控单元管理员用户的邮件地址，不需要身份验证，只有指定的ip可访问

            * 标签规则：
                xxx_log：日志单元站点
                xxx_ceph_metric：ceph监控单元
                xxx_tidb_metric：tidb监控单元
                xxx_node_metric：服务器监控单元

            http code 200:
            {
                "tag": "xxx-ceph",
                "unit": {
                    "name": "中国科技云-运维大数据",
                    "name_en": "CSTcloud AIOPS"
                },
                "emails": [
                    "xxx@qq.com",
                    "xxx@cnic.cn"
                ]
            }
            http code 400,403,404:
            {
                "code": "TargetNotExist",
                "message": "未找到指定标签标识的监控单元"
            }
            400: InvalidArgument    # 参数无效
            403: AccessDenied   # ip不允许访问
            404: TargetNotExist
        """
        tag = request.query_params.get('tag', None)

        if tag is None:
            return self.exception_response(errors.InvalidArgument(message=_('必须指定监控单元标识标签')))

        if not tag:
            return self.exception_response(errors.InvalidArgument(message=_('指定监控单元标识标签无效')))

        try:
            MonitorEmailAddressIPRestrictor().check_restricted(request)
        except errors.AccessDenied as exc:
            return self.exception_response(exc)

        tag = tag.strip(' ')
        unit = self.try_get_unit(tag=tag)
        if unit is None:
            return self.exception_response(
                errors.TargetNotExist(message=_('未找到指定标签标识的监控单元')))

        odc_id = unit.org_data_center_id
        unit_admin_emails = set(unit.users.values_list('username', flat=True))
        if odc_id:
            odc_admin_emails = set(OrgDataCenter.objects.get(id=odc_id).users.values_list('username', flat=True))
            unit_admin_emails.update(odc_admin_emails)

        emails = list(set(unit_admin_emails))
        return Response(data={
            'tag': tag,
            'unit': {
                'name': unit.name, 'name_en': unit.name_en
            },
            'emails': emails
        })

    @staticmethod
    def try_get_unit(tag: str) -> Union[MonitorJobCeph, MonitorJobTiDB, MonitorJobServer, LogSite, None]:
        low_tag = tag.lower()
        if low_tag.endswith('_log'):
            return LogSite.objects.filter(job_tag=tag).first()
        elif '_ceph_' in low_tag:
            return MonitorJobCeph.objects.filter(job_tag=tag).first()
        elif '_tidb_' in low_tag:
            return MonitorJobTiDB.objects.filter(job_tag=tag).first()
        elif '_node_' in low_tag:
            return MonitorJobServer.objects.filter(job_tag=tag).first()
        else:
            unit = LogSite.objects.filter(job_tag=tag).first()
            if unit is not None:
                return unit
            unit = MonitorJobCeph.objects.filter(job_tag=tag).first()
            if unit is not None:
                return unit
            unit = MonitorJobTiDB.objects.filter(job_tag=tag).first()
            if unit is not None:
                return unit
            unit = MonitorJobServer.objects.filter(job_tag=tag).first()
            if unit is not None:
                return unit

        return None
