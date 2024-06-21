from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from utils.paginators import NoPaginatorInspector
from apps.api.viewsets import NormalGenericViewSet
from apps.app_global.configs_manager import global_configs


class SalesCustomerServiceViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('销售客户人员联系信息'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        销售客户人员联系信息

            http Code 200 Ok:
                {
                  "info": "xxx",
                }
        """
        info = global_configs.get(global_configs.ConfigName.SALES_CUSTOMER_SERVICE_INFO.value)
        return Response(data={'info': info})

    def get_serializer_class(self):
        return Serializer
