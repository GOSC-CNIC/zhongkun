from django.utils.translation import gettext_lazy, gettext as _
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.serializers import log_serializers
from api.paginations import NewPageNumberPagination100
from api.handlers.log_handler import LogSiteHandler
from monitor.models import LogSite
from utils.paginators import NoPaginatorInspector


PARAM_LOKI_TIMESTAMP_RANGE = [
    openapi.Parameter(
        name='start',
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_INTEGER,
        required=True,
        description='起始时间戳(s,ns)'
    ),
    openapi.Parameter(
        name='end',
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_INTEGER,
        required=True,
        description='结束时间戳(s,ns)'
    ),
]
PARAM_LOKI_BASE = [
    openapi.Parameter(
        name='direction',
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        required=False,
        default="backward",
        description='日志的排序顺序(可选backward、forward)'
    ),
    openapi.Parameter(
        name='limit',
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_NUMBER,
        required=False,
        default=1000,
        description='要返回的最大条目数(默认1000条)'
    ),
]
PARAM_LOKI = PARAM_LOKI_TIMESTAMP_RANGE + PARAM_LOKI_BASE


class LogSiteViewSet(CustomGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举有访问权限的日志单元'),
        manual_parameters=[
            openapi.Parameter(
                name='log_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=_('筛选日志类型的日志单元') + f'{LogSite.LogType.choices}'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举有权限的日志单元

            Http Code: 状态码200，返回数据：
            {
                "count": 1,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "id": "93cg24r8xo3u1ku9rxrwhm7sh",
                        "name": "name4",
                        "name_en": "name_en4",
                        "log_type": "http", # http, nat
                        "job_tag": "job_tag4",
                        "sort_weight": 8,
                        "desc": "",
                        "creation": "2023-07-21T02:28:40.594023Z",
                        "organization": {
                            "id": "93c1e1s0mxiq7qw7uo73854jh",
                            "name": "test",
                            "name_en": "test en",
                            "abbreviation": "t",
                            "sort_weight": 0,
                            "creation_time": "2023-07-21T02:28:40.588662Z"
                        },
                        "site_type": {
                            "id": "93c4yznywgm43r0v8o1479dnc",
                            "name": "obj",
                            "name_en": "obj en",
                            "sort_weight": 6,
                            "desc": ""
                        }
                    }
                ]
            }
        """
        return LogSiteHandler.list_log_site(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('站点日志查询'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=PARAM_LOKI + [
            openapi.Parameter(
                name='log_site_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('日志单元站点id')
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=_('关键字搜索')
            ),
        ],
        responses={
            200: ""
        }
    )
    @action(methods=['GET'], detail=False, url_path='query', url_name='query')
    def log_query(self, request, *args, **kwargs):
        """
        日志单元站点日志查询

            http code 200 ok:
            [
              {
                "stream": {
                  "filename": "/dev/shm/nginx/iharbor.log",
                  "job": "obs"
                },
                "values": [
                  [
                    "1689929179779377455",
                    "10.100.50.84 [21/Jul/2023:16:46:19 +0800] 159.226.171.38 200 10486084 17 obs.cstcloud.cn \"POST /api/v2/obj/fast-obs/chy-fast/NSA29476/NSA29476_onoff-M08_0006.fits?offset=2044723200&reset=false HTTP/1.1\" \"-\""
                  ],
                  [
                    "1689929179779373108",
                    "10.100.50.74 [21/Jul/2023:16:46:19 +0800] 159.226.171.37 200 10486083 17 obs.cstcloud.cn \"POST /api/v2/obj/fast-obs/chy-fast/NSA29496/NSA29496_onoff-M07_0044.fits?offset=702545920&reset=false HTTP/1.1\" \"-\""
                  ]
                ]
              }
            ]
        """
        return LogSiteHandler().log_query(view=self, request=request)

    @method_decorator(cache_page(30))
    @swagger_auto_schema(
        operation_summary=gettext_lazy('站点日志数量时序数据查询'),
        manual_parameters=PARAM_LOKI_TIMESTAMP_RANGE + [
            openapi.Parameter(
                name='log_site_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=_('日志单元站点id')
            ),
        ],
        responses={
            200: ""
        }
    )
    @action(methods=['GET'], detail=False, url_path='time-count', url_name='time-count')
    def list_time_count(self, request, *args, **kwargs):
        """
        站点日志数量时序数据查询

            http code 200 ok:
            {
              "count": 1,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "id": "tm4ryppmrid8va8wdg7s831i4",
                  "timestamp": 1690357343,
                  "count": 103,
                  "site_id": "0qd8n7qo48v431e4tsruf0ip6"
                }
              ]
            }

        """
        return LogSiteHandler().list_time_count(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return log_serializers.LogSiteSerializer

        return Serializer
