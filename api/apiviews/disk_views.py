from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.serializers import disk_serializers
from api.paginations import NewPageNumberPagination
from api.handlers.disk_handler import DiskHandler
from utils.paginators import NoPaginatorInspector


class DisksViewSet(CustomGenericViewSet):
    """
    云硬盘视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建云硬盘'),
        responses={
            200: '''    
                {
                    "order_id": "xxx",      # 订单id
                }
            '''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建云硬盘

            * 预付费模式时，请求成功会创建一个待支付的订单，支付订单成功后，订购的资源才会创建交付；
            * 按量计费模式时，请求成功会创建一个已支付订单，订购的资源会立即创建交付；

            http Code 200 Ok:
                {
                    "order_id": "xxx"
                }

            Http Code 400, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                BadRequest: 请求出现语法错误
                InvalidAzoneId: "azone_id"参数不能为空字符
                MissingPayType: 必须指定付费模式参数"pay_type"
                InvalidPayType: 付费模式参数"pay_type"值无效
                InvalidPeriod: 订购时长参数"period"值必须大于0 / 订购时长最长为5年
                MissingPeriod： 预付费模式时，必须指定订购时长
                InvalidVoId: vo不存在
                MissingServiceId：参数service_id不得为空
                InvalidServiceId：无效的服务id
                InvalidAzoneId: 指定的可用区azone_id不存在

                403:
                AccessDenied: 你不是组管理员，没有组管理权限

                409:
                BalanceNotEnough: 余额不足
                QuotaShortage: 指定服务无法提供足够的资源

                500:
                InternalError: xxx
        """
        return DiskHandler().disk_order_create(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'create':
            return disk_serializers.DiskCreateSerializer

        return Serializer
