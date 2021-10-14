from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.handlers.service_quota_handler import StatsQuotaHandler


class StatsQuotaViewSet(CustomGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('统计已发放的待使用的用户资源配额'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='条件参数，服务端点id，只统计指定服务可用的用户资源配额'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        统计已发放的待使用的用户资源配额

            http code 200：
            {
              "private_ip_total_count": 18,
              "private_ip_used_count": 10,
              "public_ip_total_count": 12,
              "public_ip_used_count": 3,
              "vcpu_total_count": 35,
              "vcpu_used_count": 17,
              "ram_total_count": 112640,                    # Mb
              "ram_used_count": 17728,
              "disk_size_total_count": 0,                   # Gb
              "disk_size_used_count": 0,
              "stats_time": "2021-10-14T06:29:51.514100Z",
              "service_id": null
            }
        """
        return StatsQuotaHandler.stats_user_quota(view=self, request=request, kwargs=kwargs)

