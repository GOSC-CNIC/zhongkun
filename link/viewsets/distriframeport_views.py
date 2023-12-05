from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import NormalGenericViewSet
from api.paginations import NewPageNumberPagination
from link.handlers.distriframeport_handler import DistriFramePortHandler
from link.serializers.distriframeport_serializer import DistriFramePortSerializer
from link.permissions import LinkIPRestrictPermission


class DistriFramePortViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举配线架端口'),
        manual_parameters=[
            openapi.Parameter(
                name='is_linked',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='过滤条件，false：未接入；true：已接入；不填查询全部'
            ),
            openapi.Parameter(
                name='frame_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='过滤条件，有值则查询配线架id下的端口，不填查询全部'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举配线架端口信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": true, # 是否接入链路
                            "element_id": "mgcj1voii43a8xd1d0j56hre7",  # 网元id
                            "link_id": [
                                "t1hgf0ngc901dop1w6f8njo1w" # 链路id
                            ],
                            "id": "mgciudagi8j8q9994go07ykyn",
                            "number": "test(1,1)", # 编号
                            "row": 1, # 行号
                            "col": 1, # 列号
                            "distribution_frame": {
                                "id": "mgcgpi7fj115jresrmzazmoy7",
                                "number": "东侧数据处理区中间机柜35至36U_中天科技ODF"
                            }
                        }
                    ]
                }
        """
        return DistriFramePortHandler.list_distriframeport(view=self, request=request)

    def get_serializer_class(self):
        return DistriFramePortSerializer
