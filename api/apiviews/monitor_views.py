from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import DefaultPageNumberPagination
from api.handlers.monitor_ceph import MonitorCephQueryHandler
from monitor.managers import MonitorJobCephManager, CephQueryChoices


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
                "metric": {
                  "__name__": "ceph_health_status",
                  "instance": "10.0.200.100:9283",
                  "job": "Fed-ceph",
                  "receive_cluster": "obs",
                  "receive_replica": "0",
                  "tenant_id": "default-tenant"
                },
                "value": [
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
        """
        return MonitorCephQueryHandler().query(view=self, request=request, kwargs=kwargs)


