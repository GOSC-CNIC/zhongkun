from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import NormalGenericViewSet
from api.paginations import NewPageNumberPagination
from link.handlers.opticalfiber_handler import OpticalFiberHandler
from link.serializers.opticalfiber_serializer import OpticalFiberSerializer
from link.permissions import LinkIPRestrictPermission


class OpticalFiberViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举光纤'),
        deprecated=True,
        manual_parameters=[
            openapi.Parameter(
                name='is_linked',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='过滤条件，false：未接入；true：已接入；不填查询全部'
            ),
            openapi.Parameter(
                name='cable_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='过滤条件，有值则查询光缆id下的光纤，不填查询全部'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举光纤信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": true, # 是否接入链路
                            "element_id": "mgb3k0t02f0m954adqenm950n", # 网元id
                            "link_id": [
                                "t1hgf0ngc901dop1w6f8njo1w" # 链路id
                            ],
                            "id": "mgb3ciey2jgjqh0i56ihnpzk2",
                            "sequence": 1, # 纤序
                            "fiber_cable": {
                                "id": "mgb1bi5zka5c0dyrgo0m89sq7",
                                "number": "test-fibercable-number-1"
                            }
                        }
                    ]
                }
        """
        return OpticalFiberHandler.list_opticalfiber(view=self, request=request)

    def get_serializer_class(self):
        return OpticalFiberSerializer
