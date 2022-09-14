from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors
from api.viewsets import StorageGenericViewSet
from api.paginations import DefaultPageNumberPagination
from api.serializers import storage as storage_serializers
from storage.managers import ObjectsServiceManager
from storage.models import ObjectsService


class ObjectsServiceViewSet(StorageGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[^/]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举对象存储服务单元'),
        manual_parameters=[
            openapi.Parameter(
                name='center_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='联邦成员机构id'
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询条件，服务单元服务状态, {ObjectsService.Status.choices}'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举对象存储服务单元

            http code 200：
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "4fa94896-29a6-11ed-861f-c8009fe2ebbc",
                  "name": "test iharbor",
                  "name_en": "en iharbor",
                  "service_type": "iharbor",
                  "endpoint_url": "http://159.226.235.188:8001",
                  "add_time": "2022-09-01T03:29:39.620469Z",
                  "status": "enable",   # enable：服务中；disable：停止服务；deleted：删除
                  "remarks": "test",
                  "provide_ftp": true,
                  "ftp_domains": ["127.0.0.1", "0.0.0.0"],
                  "longitude": 0,
                  "latitude": 0,
                  "pay_app_service_id": "ss",
                  "data_center": {
                    "id": "1",
                    "name": "网络中心",
                    "name_en": "cnic"
                  }
                }
              ]
            }
        """
        center_id = request.query_params.get('center_id', None)
        status = request.query_params.get('status', None)

        if status is not None and status not in ObjectsService.Status.values:
            return self.exception_response(
                exc=errors.InvalidArgument(message=_('参数“status”的值无效'), code='InvalidStatus'))

        qs = ObjectsServiceManager.get_service_queryset()
        if center_id:
            qs = qs.filter(data_center_id=center_id)

        if status:
            qs = qs.filter(status=status)

        try:
            services = self.paginate_queryset(queryset=qs)
            serializer = self.get_serializer(services, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'list':
            return storage_serializers.ObjectsServiceSerializer

        return Serializer
