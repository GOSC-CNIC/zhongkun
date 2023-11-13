from api.viewsets import NormalGenericViewSet
from django.utils.translation import gettext_lazy, gettext as _
from api.paginations import NewPageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from link.handlers.elementlink_handler import ElementLinkHandler
from link.serializers.elementlink_serializer import ElementLinkSerializer
from drf_yasg import openapi
from rest_framework.decorators import action
from link.models import ElementLink

class ElementLinkViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举链路'),
        manual_parameters=[
            openapi.Parameter(
                name='task_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='过滤条件，有值则查询业务的所有链路，不填查询全部'
            ),
            openapi.Parameter(
                name='link_status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_STRING
                ),
                required=False,
                description=f'过滤条件，有值则查询状态符合的所有链路，不填查询全部, {ElementLink.LinkStatus.choices}'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举链路信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "id": "mghd5cum4mkqc9bwk5qq987kn",
                            "number": "link-test-number-2", # 链路编号
                            "remarks": "", # 备注
                            "link_status": "using", # 链路状态 using(使用) idle(闲置) backup(备用) deleted(删除)
                            "task": {
                                "id": "mgdzvt8zc7dbff6gt09nz4qfx",
                                "number": "KY23092702",
                                "user": "空天院-中国遥感卫星地面站"
                            },
                            "element_id_list": [
                                "mfv6evkstbaq21kcayqon2p3n",
                                "mg1gcpxh6ysk19ax8ainvyp2x",
                                "mg5i7ppqgg8jzg8hf7n3dbens",
                                "mg9am3484v1qi1dfo1tztce7n",
                                "mgarja3xdy80ubxv2jm6teo62",
                                "mgb7awdvj5ru2esyy0tybxxzs",
                                "mgcnm31ow2p8x9ug95u3qpif2"
                            ] # 组成链路的设备的网元id
                        }
                    ]
                }

        """
        return ElementLinkHandler.list_elementlink(view=self, request=request)
    
    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个链路'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个链路

            http Code 200 Ok:
                {
                    "id": "mghd5cum4mkqc9bwk5qq987kn",
                    "number": "link-test-number-2", # 链路编号
                    "remarks": "", # 备注
                    "link_status": "using", # 链路状态 using(使用) idle(闲置) backup(备用) deleted(删除)
                    "task": {
                        "id": "mgdzvt8zc7dbff6gt09nz4qfx",
                        "number": "KY23092702",
                        "user": "空天院-中国遥感卫星地面站"
                    },
                    "element_id_list": [
                        "mfv6evkstbaq21kcayqon2p3n",
                        "mg1gcpxh6ysk19ax8ainvyp2x",
                        "mg5i7ppqgg8jzg8hf7n3dbens",
                        "mg9am3484v1qi1dfo1tztce7n",
                        "mgarja3xdy80ubxv2jm6teo62",
                        "mgb7awdvj5ru2esyy0tybxxzs",
                        "mgcnm31ow2p8x9ug95u3qpif2"
                    ] # 组成链路的设备的网元id
                }
        """
        return ElementLinkHandler.retrieve_elementlink(view=self, request=request, kwargs=kwargs)



    def get_serializer_class(self):
        return ElementLinkSerializer
