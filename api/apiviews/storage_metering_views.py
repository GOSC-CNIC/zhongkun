from django.utils.translation import gettext_lazy
from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import MeteringPageNumberPagination
from api.handlers.metering_handler import MeteringHandler, MeteringObsHandler
from api.serializers import serializers

class MeteringStorageViewSet(CustomGenericViewSet):
    queryset = QuerySet().none()
    permission_classes = [IsAuthenticated, ]
    pagination_class = MeteringPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举对象存储用量计费账单'),
        request_body=no_body,
        manual_parameters=[
                              openapi.Parameter(
                                  name='service_id',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=f'查询指定服务'
                              ),
                              openapi.Parameter(
                                  name='bucket_id',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('查询指定存储桶')
                              ),
                              openapi.Parameter(
                                  name='date_start',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('计费账单日期起，默认当前月起始日期，ISO8601格式：YYYY-MM-dd')
                              ),
                              openapi.Parameter(
                                  name='date_end',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('计费账单日期止，默认当前月当前日期，ISO8601格式：YYYY-MM-dd')
                              ),
                              openapi.Parameter(
                                  name='user_id',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_STRING,
                                  required=False,
                                  description=gettext_lazy('查询指定用户的计费账单，仅以管理员身份查询时使用')
                              ),
                          ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN + [
                              openapi.Parameter(
                                  name='download',
                                  in_=openapi.IN_QUERY,
                                  type=openapi.TYPE_BOOLEAN,
                                  required=False,
                                  description=gettext_lazy('查询结果以文件方式下载文件；分页参数无效，不分页返回所有数据')
                              ),
                          ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举对象存储用量计费账单
            http code 200：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "id": "400ad412-b265-11ec-9dad-c8009fe2eb10",
                  "original_amount": "2.86",
                  "trade_amount": "0.00",
                  "daily_statement_id": "",
                  "service_id": "8d725d6a-30b5-11ec-a8e6-c8009fe2eb10",
                  "storage_bucket_id": "d24aa2fc-5d43-11ec-8f46-c8009fe2eb10",
                  "date": "2021-12-15",
                  "creation_time": "2022-04-02T09:14:07.754058Z",
                  "user_id": "1",
                  "username": "admin",
                  "storage": 45.64349609833334
                }
            }
        """
        return MeteringObsHandler().list_bucket_metering(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.MeteringStorageSerializer

        return Serializer