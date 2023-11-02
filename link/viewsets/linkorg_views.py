from api.viewsets import NormalGenericViewSet
from django.utils.translation import gettext_lazy, gettext as _
from api.paginations import NewPageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from link.handlers.linkorg_handler import LinkOrgHandler
from link.serializers.linkorg_serializer import LinkOrgSerializer
from drf_yasg import openapi
from rest_framework.decorators import action


class linkOrgViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举链路二级机构'),
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举链路二级机构信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "id": "mfr1i5nitwi6p13hg5extsvvx",
                            "name": "中国遥感卫星地面站", # 二级机构名
                            "remarks": "", # 备注
                            "location": "116.376313,-39.863116", # 经纬度
                            "data_center": {
                                "id": "mgdzvt8zc7dbff6gt09nz4qfx",
                                "name": "test",
                                "name_en": "test"
                            }
                        }
                    ]
                }

        """
        return LinkOrgHandler.list_linkorg(view=self, request=request)
    

    def get_serializer_class(self):
        return LinkOrgSerializer
