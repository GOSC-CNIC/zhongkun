from django.utils.translation import gettext_lazy
from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from metering.models import PaymentStatus
from api.paginations import MeteringPageNumberPagination, StatementPageNumberPagination
from api.handlers.metering_handler import MeteringHandler, StatementHandler
from api.serializers import serializers


class MeteringServerViewSet(CustomGenericViewSet):
    queryset = QuerySet().none()
    permission_classes = [IsAuthenticated, ]
    pagination_class = MeteringPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举云主机用量计费账单'),
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
                name='server_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定云主机')
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
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定VO组的计费账单，需要vo组权限, 或管理员权限，不能与user_id同时使用')
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
        列举云主机用量计费账单

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
                  "server_id": "d24aa2fc-5d43-11ec-8f46-c8009fe2eb10",
                  "date": "2021-12-15",
                  "creation_time": "2022-04-02T09:14:07.754058Z",
                  "user_id": "1",
                  "username": "admin",
                  "vo_id": "",
                  "vo_name": "",
                  "owner_type": "user",     # user: 属于用户；vo: 属于vo组
                  "cpu_hours": 45.64349609833334,
                  "ram_hours": 91.28699219666667,
                  "disk_hours": 0,
                  "public_ip_hours": 22.82174804916667,
                  "snapshot_hours": 0,
                  "upstream": 0,
                  "downstream": 0,
                  "pay_type": "postpaid"
                }
            }
        """
        return MeteringHandler().list_server_metering(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('按云主机uuid显示云主机计量计费聚合列表'),
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
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定VO组的聚合计量计费信息，需要vo组权限, 或管理员权限，不能与user_id同时使用')
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
                description=gettext_lazy('查询指定服务')
            ),
        ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='download',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description=gettext_lazy('查询结果以文件方式下载文件；分页参数无效，不分页返回所有数据')
            ),
        ]
    )
    @action(methods=['GET'], detail=False, url_path='aggregation/server', url_name='aggregation-by-server')
    def aggregation_by_server(self, request, *args, **kwargs):
        """
        列举指定时间段内每个server计量计费单聚合

            http code 200:
            {
              "count": 240,
              "page_num": 1,
              "page_size": 100,
              "results": [
                "server_id": "006621ec-36f8-11ec-bc59-c8009fe2eb03",
                "total_cpu_hours": 19200.0,
                "total_ram_hours": 38400.0,
                "total_disk_hours": 0.0,
                "total_public_ip_hours": 2400.0,
                "total_original_amount": 3810.0,
                "total_trade_amount": 123.00,
                "service_name": "科技云联邦研发与运行",           
                "server": {                                   
                    "id": "006621ec-36f8-11ec-bc59-c8009fe2eb03",
                    "ipv4": "159.226.235.52",
                    "ram": 16384,
                    "vcpus": 8
                }
              ]
            }
        """
        return MeteringHandler().list_aggregation_by_server(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('按用户id显示云主机计量计费聚合列表'),
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
                description=gettext_lazy('查询指定服务')
            ),                   
        ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='download',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description=gettext_lazy('查询结果以文件方式下载文件；分页参数无效，不分页返回所有数据')
            ),
        ]
    )
    @action(methods=['GET'], detail=False, url_path='aggregation/user', url_name='aggregation-by-user')
    def aggregation_by_user(self, request, *args, **kwargs):
        """
        列举指定时间段内每个用户所有server计量计费单聚合

            200:
            {
              "count": 62,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "user_id": "0443ba18-0093-11ec-9a41-c8009fe2eb03",
                  "total_original_amount": 62613.84,
                  "total_trade_amount": 0,
                  "total_server": 7,
                  "user": {
                    "id": "0443ba18-0093-11ec-9a41-c8009fe2eb03",
                    "username": "zhouquan@cnic.cn",
                    "company": "cnic"
                  }
                }
              ]
            }
        """
        return MeteringHandler().list_aggregation_by_user(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('按vo组显示云主机计量计费聚合列表'),
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
                description=gettext_lazy('查询指定服务')
            ),                   
        ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='download',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description=gettext_lazy('查询结果以文件方式下载文件；分页参数无效，不分页返回所有数据')
            ),
        ]
    )
    @action(methods=['GET'], detail=False, url_path='aggregation/vo', url_name='aggregation-by-vo')
    def aggregation_by_vo(self, request, *args, **kwargs):
        """
        列举指定时间段内每个vo组所有server计量计费单聚合

            200：
            {
              "count": 8,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "vo_id": "1d35892c-36d3-11ec-8e3b-c8009fe2eb03",
                  "total_original_amount": 2885.39,
                  "total_trade_amount": 0,
                  "total_server": 3,
                  "vo": {
                    "id": "1d35892c-36d3-11ec-8e3b-c8009fe2eb03",
                    "name": "科研计算云联邦演示",
                    "company": "中国科学院计算机网络信息中心"
                  }
                }
              ]
            }
        """
        return MeteringHandler().list_aggregation_by_vo(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('按服务节点显示云主机计量计费聚合列表'),
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
        ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='download',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description=gettext_lazy('查询结果以文件方式下载文件；分页参数无效，不分页返回所有数据')
            ),
        ]
    )
    @action(methods=['GET'], detail=False, url_path='aggregation/service', url_name='aggregation-by-service')
    def aggregation_by_service(self, request, *args, **kwargs):
        """
        列举指定时间段内每个服务节点所有server计量计费单聚合

            200:
            {
              "count": 4,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "service_id": "1",
                  "total_original_amount": 508142.16,
                  "total_trade_amount": 0,
                  "total_server": 182,
                  "service": {
                    "id": "1",
                    "name": "科技云联邦研发与运行"
                  }
                }
              ]
            }
        """
        return MeteringHandler().list_aggregation_by_service(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.MeteringServerSerializer

        return Serializer


class StatementServerViewSet(CustomGenericViewSet):
    # queryset = QuerySet().none()
    permission_classes = [IsAuthenticated, ]
    pagination_class = StatementPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

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
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询指定VO组的日结算单'
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
                  "vo_id": "1d35892c-36d3-11ec-8e3b-c8009fe2eb03",
                  "vo_name": "科研计算云联邦演示",
                  "owner_type": "vo",
                  "service": {
                    "id": "1d35892c-36d3-11ec-8e3b-c8009fe2eb03",
                    "name": "科技云联邦研发与运行",
                    "name_en": "CSTCloud Federation Dev & Ops",
                    "service_type": "evcloud"
                  }
                }
              ]
            }
        """
        return StatementHandler().list_statement_server(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('日结算单详情'),
        request_body=no_body,
        manual_parameters=[
        ],
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
              "vo_id": "1d35892c-36d3-11ec-8e3b-c8009fe2eb03",
              "vo_name": "科研计算云联邦演示",
              "owner_type": "vo",
              "service": {
                "id": "1",
                "name": "科技云联邦研发与运行",
                "name_en": "CSTCloud Federation Dev & Ops",
                "service_type": "evcloud"
              }
            }
        """
        return StatementHandler().statement_server_detail(view=self, request=request, kwargs=kwargs)   

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.DailyStatementServerDetailSerializer
        elif self.action == 'retrieve':
            return serializers.DailyStatementServerDetailSerializer

        return Serializer
