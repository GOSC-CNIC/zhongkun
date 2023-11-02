from api.viewsets import NormalGenericViewSet
from django.utils.translation import gettext_lazy, gettext as _
from api.paginations import NewPageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from link.handlers.connectorbox_handler import ConnectorBoxHandler
from link.serializers.connectorbox_serializer import ConnectorBoxSerializer
from drf_yasg import openapi


class ConnectorBoxViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举接头盒'),
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举配线架信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": true, # 是否接入链路
                            "element_id": "mgarja3xdy80ubxv2jm6teo62", # 网元id
                            "id": "mgarbd5pg0zkmavtitu5gbxzc",
                            "number": "熔纤包测试1", # 编号
                            "place": "", # 设备位置
                            "remarks": "", # 备注
                            "location": "" # 经纬度
                        }
                    ]
                }

        """
        return ConnectorBoxHandler.list_connectorbox(view=self, request=request)
    

    def get_serializer_class(self):
        return ConnectorBoxSerializer
