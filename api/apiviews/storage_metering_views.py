from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from metering.models import PaymentStatus
from api.paginations import MeteringPageNumberPagination, StatementPageNumberPagination
from api.handlers.metering_handler import MeteringObsHandler, StorageStatementHandler
from api.serializers import serializers


class MeteringStorageViewSet(CustomGenericViewSet):
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
                  "storage": 45.64349609833334,
                  "service": {
                    'id': '287bd860-5994-11ed-ae92-c8009fe2ebbc',
                    'name': 'service2',
                    'name_en': 'xxx'
                  }
                }
            }
        """
        return MeteringObsHandler().list_bucket_metering(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.MeteringStorageSerializer

        return Serializer


class AdminMeteringStorageViewSet(CustomGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = MeteringPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定时间段内存储桶计量计费聚合数据'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('聚合日期起，默认当前月起始日期，ISO8601格式：YYYY-MM-dd')
            ),
            openapi.Parameter(
                name='date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('聚合日期止，默认当前月当前日期，ISO8601格式：YYYY-MM-dd')
            ),
            openapi.Parameter(
                name='user_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定用户的聚合计量计费信息，仅以管理员身份查询时使用')
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定存储服务单元')
            ),
            openapi.Parameter(
                name='bucket_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定存储桶')
            ),
            openapi.Parameter(
                name='order_by',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'指定排序，默认按桶id正序，{MeteringObsHandler.AGGREGATION_BUCKET_ORDER_BY_CHOICES}'
            ),
            # openapi.Parameter(
            #     name='download',
            #     in_=openapi.IN_QUERY,
            #     type=openapi.TYPE_BOOLEAN,
            #     required=False,
            #     description=gettext_lazy('查询结果以文件方式下载文件；分页参数无效，不分页返回所有数据')
            # ),
        ]
    )
    @action(methods=['GET'], detail=False, url_path='aggregation/bucket', url_name='aggregation-by-bucket')
    def aggregation_by_bucket(self, request, *args, **kwargs):
        """
        查询指定时间段内存储桶计量计费聚合数据

            http code 200:
            {
                "count": 18,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "storage_bucket_id": "c50c81ea-59bf-11ed-97e1-c8009fe2eb03",
                        "total_storage_hours": 182151079.65071514,
                        "total_downstream": 0.0,
                        "total_get_request": 0,
                        "total_original_amount": "0.00",    # 计费金额
                        "total_trade_amount": "0.00",       # 应付金额 / 实付金额
                        "service": {
                            "id": "0fb92e48-3565-11ed-9877-c8009fe2eb03",
                            "name": "中国科技云对象存储服务"
                        },
                        "user": {
                            "id": "23af47ae-ee83-11eb-8f3c-c8009fe2eb03",
                            "username": "wxz@cnic.cn"
                        },
                        "bucket": {
                            "id": "c50c81ea-59bf-11ed-97e1-c8009fe2eb03",
                            "name": "databox-arc"
                        }
                    }
                ]
            }
        """
        return MeteringObsHandler().list_aggregation_by_bucket(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定时间段内用户的存储桶计量计费聚合数据'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('聚合日期起，默认当前月起始日期，ISO8601格式：YYYY-MM-dd')
            ),
            openapi.Parameter(
                name='date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('聚合日期止，默认当前月当前日期，ISO8601格式：YYYY-MM-dd')
            ),
            openapi.Parameter(
                name='user_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定用户的聚合计量计费信息，仅以管理员身份查询时使用')
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定存储服务单元')
            ),
            openapi.Parameter(
                name='order_by',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'指定排序，默认按桶id正序，{MeteringObsHandler.AGGREGATION_USER_ORDER_BY_CHOICES}'
            ),
        ]
    )
    @action(methods=['GET'], detail=False, url_path='aggregation/user', url_name='aggregation-by-user')
    def aggregation_by_user(self, request, *args, **kwargs):
        """
        查询指定时间段内用户的存储桶计量计费聚合数据

            http code 200:
            {
                "count": 18,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "user_id": "c50c81ea-59bf-11ed-97e1-c8009fe2eb03",
                        "username": "wxz@cnic.cn"
                        "total_storage_hours": 182151079.65071514,
                        "total_downstream": 0.0,
                        "total_get_request": 0,
                        "total_original_amount": "0.00",    # 计费金额
                        "total_trade_amount": "0.00",       # 应付金额 / 实付金额
                        "bucket_count": 10                  # 时间段内计量的桶的数量
                    }
                ]
            }
        """
        return MeteringObsHandler().list_aggregation_by_user(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定时间段内服务单元的存储桶计量计费聚合数据'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('聚合日期起，默认当前月起始日期，ISO8601格式：YYYY-MM-dd')
            ),
            openapi.Parameter(
                name='date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('聚合日期止，默认当前月当前日期，ISO8601格式：YYYY-MM-dd')
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定存储服务单元')
            ),
            openapi.Parameter(
                name='order_by',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'指定排序，默认按桶id正序，{MeteringObsHandler.AGGREGATION_SERVICE_ORDER_BY_CHOICES}'
            ),
            # openapi.Parameter(
            #     name='download',
            #     in_=openapi.IN_QUERY,
            #     type=openapi.TYPE_BOOLEAN,
            #     required=False,
            #     description=gettext_lazy('查询结果以文件方式下载文件；分页参数无效，不分页返回所有数据')
            # ),
        ]
    )
    @action(methods=['GET'], detail=False, url_path='aggregation/service', url_name='aggregation-by-service')
    def aggregation_by_service(self, request, *args, **kwargs):
        """
        查询指定时间段内服务单元的存储桶计量计费聚合数据

            http code 200:
            {
                "count": 18,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "service_id": "c50c81ea-59bf-11ed-97e1-c8009fe2eb03",
                        "total_storage_hours": 182151079.65071514,
                        "total_downstream": 0.0,
                        "total_get_request": 0,
                        "total_original_amount": "0.00",    # 计费金额
                        "total_trade_amount": "0.00",       # 应付金额 / 实付金额
                        "bucket_count": 10                  # 时间段内计量的服务单元桶的数量
                        "service": {
                            "id": "xxx",
                            "name": "xxx",
                        }
                    }
                ]
            }
        """
        return MeteringObsHandler().list_aggregation_by_service(view=self, request=request)

    def get_serializer_class(self):
        return Serializer


class StatementStorageViewSet(CustomGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = StatementPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举日结算单'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='payment_status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付状态，{PaymentStatus.choices}'
            ),
            openapi.Parameter(
                name='date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'日结算单日期查询，时间段起，ISO8601格式：YYYY-MM-dd'
            ),
            openapi.Parameter(
                name='date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'日结算单日期查询，时间段止，ISO8601格式：YYYY-MM-dd'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举日结算单

            http code 200：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "statements": [
                {
                  "id": "s7649b7e624f211ed88b9c8009fe2eb44",
                  "original_amount": "16.32",
                  "payable_amount": "0.00",
                  "trade_amount": "0.00",
                  "payment_status": "unpaid",
                  "payment_history_id": "",
                  "date": "2022-01-01",
                  "creation_time": "2022-08-26T03:52:10.358606Z",
                  "user_id": "",
                  "username": "",
                  "service": {
                    "id": "1d35892c-36d3-11ec-8e3b-c8009fe2eb03",
                    "name": "iharbor",
                    "name_en": "iharbor",
                    "service_type": "iharbor"
                  }
                }
              ]
            }
        """
        return StorageStatementHandler().list_statement_storage(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('日结算单详情'),
        request_body=no_body,
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        日结算单详情

            http code 200：
            {
              "id": "s7647061824f211ed88b9c8009fe2eb44",
              "original_amount": "16.32",
              "payable_amount": "0.00",
              "trade_amount": "0.00",
              "payment_status": "unpaid",
              "payment_history_id": "",
              "date": "2022-01-01",
              "creation_time": "2022-08-26T03:52:10.341058Z",
              "user_id": "",
              "username": "",
              "service": {
               "id": "1d35892c-36d3-11ec-8e3b-c8009fe2eb03",
                    "name": "iharbor",
                    "name_en": "iharbor",
                    "service_type": "iharbor"
              },
              "meterings": [
                {
                    "id": "b4956242685b011eda211c8009fe2ebbc",
                    "original_amount": "2.22",
                    "trade_amount": "0.00",
                    "daily_statement_id": "o4954f7b885b011eda211c8009fe2ebbc",
                    "service_id": "493890dc-85b0-11ed-a211-c8009fe2ebbc",
                    "bucket_name": "",
                    "storage_bucket_id": "bucket3",
                    "date": "2022-01-01",
                    "creation_time": "2022-12-27T06:32:50.948133Z",
                    "user_id": "492c51dc-85b0-11ed-a211-c8009fe2ebbc",
                    "username": "test",
                    "storage": 3.2345,
                    "downstream": 0.0,
                    "replication": 0.0,
                    "get_request": 0,
                    "put_request": 0
                }
              ]
            }
        """
        return StorageStatementHandler().statement_storage_detail(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.DailyStatementStorageDetailSerializer
        elif self.action == 'retrieve':
            return serializers.DailyStatementStorageDetailSerializer

        return Serializer
