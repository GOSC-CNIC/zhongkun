from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import MeteringPageNumberPagination, StatementPageNumberPagination
from apps.metering.handlers.metering_handler import MeteringMonitorSiteHandler
from apps.metering import metering_serializers
from apps.metering.models import PaymentStatus


class MeteringMonitorSiteViewSet(CustomGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = MeteringPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举站点监控用量计量计费单'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='site_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询指定站点监控任务')
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
        ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举站点监控用量计量计费单

            http code 200：
                {
                  "count": 2,
                  "page_num": 1,
                  "page_size": 100,
                  "results": [
                    {
                      "id": "8ojdxnfh0jp1m30izbn18qn8q",
                      "original_amount": "0.30",    # 计费金额
                      "trade_amount": "0.30",       # 应付金额
                      "daily_statement_id": "mw8us5dd22mae2uezh16gtmo3mv",
                      "website_id": "15ba99aa-b0ce-11ed-8fe1-c800dfc12405",
                      "website_name": "一体化云后端",
                      "user_id": "8",
                      "username": "wangyushun@cnic.cn",
                      "date": "2023-09-25",
                      "creation_time": "2023-09-26T02:27:51.417492Z",
                      "hours": 24,  # 监控小时数
                      "tamper_resistant_count": 0   # 0: 无防篡改监控；>0：有防篡改监控
                    }
                  ]
                }
        """
        return MeteringMonitorSiteHandler().list_site_metering(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return metering_serializers.MeteringMonitorSiteSerializer

        return Serializer


class StatementMonitorSiteViewSet(CustomGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = StatementPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举站点监控日结算单'),
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
        列举站点监控日结算单

            http code 200：
            {
              "count": 2,
              "page_num": 1,
              "page_size": 20,
              "statements": [
                {
                  "id": "mw8us5dd22mae2uezh16gtmo3mv",
                  "original_amount": "0.30",
                  "payable_amount": "0.30",
                  "trade_amount": "0.00",
                  "payment_status": "unpaid",
                  "payment_history_id": "",
                  "date": "2023-09-25",
                  "creation_time": "2023-09-26T02:27:53.982466Z",
                  "user_id": "8",
                  "username": "wangyushun@cnic.cn"
                }
              ]
            }
        """
        return MeteringMonitorSiteHandler().list_statement_site(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('站点监控日结算单详情'),
        request_body=no_body,
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        站点监控日结算单详情

            http code 200：
            {
              "id": "mw8us5dd22mae2uezh16gtmo3mv",
              "original_amount": "0.30",
              "payable_amount": "0.30",
              "trade_amount": "0.00",
              "payment_status": "unpaid",
              "payment_history_id": "",
              "date": "2023-09-25",
              "creation_time": "2023-09-26T02:27:53.982466Z",
              "user_id": "8",
              "username": "wangyushun@cnic.cn",
              "meterings": [
                {
                  "id": "8ojdxnfh0jp1m30izbn18qn8q",
                  "original_amount": "0.30",
                  "trade_amount": "0.30",
                  "daily_statement_id": "mw8us5dd22mae2uezh16gtmo3mv",
                  "website_id": "15ba99aa-b0ce-11ed-8fe1-c800dfc12405",
                  "website_name": "一体化云后端",
                  "user_id": "8",
                  "username": "wangyushun@cnic.cn",
                  "date": "2023-09-25",
                  "creation_time": "2023-09-26T02:27:51.417492Z",
                  "hours": 24,
                  "tamper_resistant_count": 0
                }
              ]
            }
        """
        return MeteringMonitorSiteHandler().statement_site_detail(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return metering_serializers.StatementMonitorSiteSerializer
        elif self.action == 'retrieve':
            return metering_serializers.StatementMonitorSiteSerializer

        return Serializer
