from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy
from api.paginations import ScanTaskPageNumberPagination
from api.viewsets import CustomGenericViewSet
from scan.handlers.price_handler import ScanPriceHandler


class ScanPriceViewSet(CustomGenericViewSet):
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = ScanTaskPageNumberPagination
    lookup_field = "id"

    @swagger_auto_schema(
        operation_summary=gettext_lazy("列举漏扫服务价格"),
        manual_parameters=[],
        responses={200: ""},
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户站点扫描任务和主机扫描任务价格

            Http Code: 状态码200，返回数据：
            {
              "price": {
                "web": "100.00",
                "host": "30.00"
              }
            }
            http code: 404：
            {
                "code": "xxx",
                "message": "xxx"
            }
            404：
            NotFound：安全扫描服务信息不存在
        """
        return ScanPriceHandler.get_scan_price(view=self, request=request)
