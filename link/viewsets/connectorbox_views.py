from django.utils.translation import gettext_lazy

from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import NormalGenericViewSet
from api.paginations import NewPageNumberPagination
from link.handlers.connectorbox_handler import ConnectorBoxHandler
from link.serializers.connectorbox_serializer import ConnectorBoxSerializer
from link.permissions import LinkIPRestrictPermission


class ConnectorBoxViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举接头盒'),
        deprecated=True,
        manual_parameters=[
            openapi.Parameter(
                name='is_linked',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='过滤条件，false：未接入；true：已接入；不填查询全部'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举接头盒

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": true, # 是否接入链路
                            "link_id": [
                                "t1hgf0ngc901dop1w6f8njo1w" # 链路id
                            ],
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
