from django.utils.translation import gettext_lazy, gettext as _
from django.utils.functional import lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer, DateTimeField as DRFDateTimeField
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors
from apps.api.paginations import NewPageNumberPagination100
from apps.api.viewsets import NormalGenericViewSet

from apps.app_service.models import KunYuanService
from apps.app_service import serializers
from apps.app_service.managers.kunyuan import KunYuanServiceManager


class KunYuanServiceViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举坤元服务单元'),
        manual_parameters=[
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=lazy(str, str)(KunYuanService.Status.choices)
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举坤元服务单元

            http code 200:
            {
              "count": 1,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "name": "36.33开发环境",
                  "name_en": "36.33 develop",
                  "endpoint_url": "http://xx.xx.xx.xx:8001",
                  "username": "",
                  "creation_time": "2024-11-14T07:50:40.099867Z",
                  "status": "enable",
                  "remarks": "",
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 0,
                  "version": "v3.2.0",
                  "version_update_time": "2024-11-14T08:21:42.824645Z",
                  "org_data_center": {
                    "id": "gii8wpgvtna8xvujhkf3496qo",
                    "name": "AIOps数据中心",
                    "name_en": "AIOps data center",
                    "longitude": 116.34334,
                    "latitude": 39.99288,
                    "sort_weight": -1008,
                    "organization": {
                      "id": "1",
                      "name": "中国科学院计算机网络信息中心",
                      "name_en": "Computer Network Information Center,  Chinese Academy of Sciences",
                      "sort_weight": -1
                    }
                  }
                }
              ]
            }
        """
        status = request.query_params.get('status', None)

        try:
            if status and status not in KunYuanService.Status.values:
                raise errors.InvalidArgument(message=_('无效的状态类型'))

            queryset = KunYuanService.objects.all()
            if status:
                queryset = queryset.filter(status=status)

            objs = self.paginate_queryset(queryset)
            serializer = self.get_serializer(objs, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            return self.exception_response(exc=exc)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询坤元服务版本'),
        manual_parameters=[
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=lazy(str, str)(KunYuanService.Status.choices)
            ),
        ],
        responses={
            200: ''''''
        }
    )
    @action(methods=['GET'], detail=True, url_path='version', url_name='version')
    def query_version(self, request, *args, **kwargs):
        """
        查询坤元服务版本

            * 实时去查询坤元服务，查询失败会返回错误信息

            http code 200:
            {
                "version": "v3.2.0",
                "version_update_time": "2024-11-14T08:21:42.824645Z"
            }
        """
        try:
            service = KunYuanService.objects.filter(id=kwargs[self.lookup_field]).first()
            if service is None:
                raise errors.TargetNotExist(message=_('坤元服务不存在'))

            r = KunYuanServiceManager.update_service_version(service=service)
            if r is not True:
                raise r
        except Exception as exc:
            return self.exception_response(exc=exc)

        return Response(data={
            'version': service.version,
            'version_update_time': DRFDateTimeField().to_representation(service.version_update_time)
        }, status=200)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.KunYuanServiceSerializer

        return Serializer
