from api.viewsets import NormalGenericViewSet
from django.utils.translation import gettext_lazy, gettext as _
from api.paginations import NewPageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from link.handlers.distriframe_handler import DistriFrameHandler
from link.serializers.distriframe_serializer import DistriFrameSerializer
from drf_yasg import openapi
from rest_framework.decorators import action


class DistriFrameViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举配线架'),
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
                            "id": "mgcgpi7fj115jresrmzazmoy7",
                            "number": "东侧数据处理区中间机柜35至36U_中天科技ODF",
                            "model_type": "LC",
                            "row_count": 1,
                            "col_count": 12,
                            "place": "中国资源卫星应用中心一期楼三层机房A301",
                            "remarks": "",
                            "link_org": {
                                "id": "mfr1i5nitwi6p13hg5extsvvx",
                                "name": "中国遥感卫星地面站"
                            }
                        }
                    ]
                }

        """
        return DistriFrameHandler.list_distriframe(view=self, request=request)

    def get_serializer_class(self):
        return DistriFrameSerializer
