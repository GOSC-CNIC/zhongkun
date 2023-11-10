from api.viewsets import NormalGenericViewSet
from django.utils.translation import gettext_lazy, gettext as _
from api.paginations import NewPageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from link.handlers.element_handler import ElementHandler
from link.serializers.element_data_serializer import ElementDataSerializer
from rest_framework.decorators import action


class ElementViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('根据网元id获取网元信息'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个租用线路
        
            case1:
            http Code 200 Ok:
                {
                    "type": "lease",
                    "lease": {
                        "is_linked": false,
                        "element_id": "ksss6f25mu7vx42yxhyy2gv8r",
                        "id": "cc31q7a7cz2h7trj6t3986jvd",
                        "private_line_number": "37969041",
                        "lease_line_code": "北京青岛ANE0172NP",
                        "line_username": "国家海洋局北海分局（青岛）",
                        "endpoint_a": "北京市海淀区中关村南四街4号",
                        "endpoint_z": "",
                        "line_type": "接入网",
                        "cable_type": "MSTP电路",
                        "bandwidth": 100,
                        "length": null,
                        "provider": "联通（北京）",
                        "enable_date": "2019-01-31",
                        "is_whithdrawal": false,
                        "money": null,
                        "remarks": "电路代号（长途）：北京青岛ANE0172NP，2019年1月31日开通"
                    },
                    "port": null,
                    "fiber": null,
                    "box": null
                }
                
            case2:
            http Code 200 Ok:
                {
                    "type": "port",
                    "lease": null,
                    "port": {
                        "is_linked": false,
                        "element_id": "mgd1c7adgkikaqudtunkkftkc",
                        "id": "mgd15851e9m9nix6y1v2cjvb7",
                        "number": "东侧数据处理区中间机柜35至36U_中天科技ODF(1,6)",
                        "row": 1,
                        "col": 6,
                        "distribution_frame": {
                            "id": "mgcgpi7fj115jresrmzazmoy7",
                            "number": "东侧数据处理区中间机柜35至36U_中天科技ODF"
                        }
                    },
                    "fiber": null,
                    "box": null
                }

            case3:
            http Code 200 Ok:
                {
                    "type": "fiber",
                    "lease": null,
                    "port": null,
                    "fiber": {
                        "is_linked": false,
                        "element_id": "mgbar1nvg5b7y601zrhocypzh",
                        "id": "mgbagzmookwyt4binzao7exzn",
                        "sequence": 3,
                        "fiber_cable": {
                            "id": "mgb1bi5zka5c0dyrgo0m89sq7",
                            "number": "test-fibercable-number-1"
                        }
                    },
                    "box": null
                }

            case4:
            http Code 200 Ok:
                {
                    "type": "box",
                    "lease": null,
                    "port": null,
                    "fiber": null,
                    "box": {
                        "is_linked": true,
                        "element_id": "mgarja3xdy80ubxv2jm6teo62",
                        "id": "mgarbd5pg0zkmavtitu5gbxzc",
                        "number": "熔纤包测试1",
                        "place": "熔纤包测试-位置",
                        "remarks": "",
                        "location": ""
                    }
                }
        """
        return ElementHandler.retrieve_element(view=self, request=request, kwargs=kwargs)


    def get_serializer_class(self):
        return ElementDataSerializer
