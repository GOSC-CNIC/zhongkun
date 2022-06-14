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
from monitor.managers import CephQueryChoices, ServerQueryChoices, VideoMeetingQueryChoices


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
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('服务id, 查询指定服务Cpph集群')
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
                "monitor": {
                  "name": "云联邦研发测试Ceph集群",
                  "name_en": "云联邦研发测试Ceph集群",
                  "job_tag": "Fed-ceph",
                  "service_id": "2",
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
            name='service_id',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            required=True,
            description=_('服务id，查询指定服务Ceph集群')
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
                "monitor": {
                  "name": "云联邦研发测试Ceph集群",
                  "name_en": "云联邦研发测试Ceph集群",
                  "job_tag": "Fed-ceph",
                  "service_id": "2",
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
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('服务id, 查询指定服务集群')
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
                "monitor": {
                  "name": "大规模对象存储云主机服务物理服务器监控",
                  "name_en": "大规模对象存储云主机服务物理服务器监控",
                  "job_tag": "obs-node",
                  "service_id": "1",
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