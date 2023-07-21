from django.utils.translation import gettext_lazy, gettext as _
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

    def get_serializer_class(self):
        if self.action == 'list':
            return log_serializers.LogSiteSerializer

        return Serializer
