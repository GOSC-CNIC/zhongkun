from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import NormalGenericViewSet
from api.paginations import NewPageNumberPagination
from link.handlers.link_handler import LinkHandler
from link.serializers.link_serializer import LinkSerializer, CreatLinkSerializer
from link.models import Link
from link.permissions import LinkIPRestrictPermission


class LinkViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举链路'),
        deprecated=True,
        manual_parameters=[
            openapi.Parameter(
                name='link_status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_STRING
                ),
                required=False,
                description=f'过滤条件，有值则查询状态符合的所有链路，不填查询全部, {Link.LinkStatus.choices}'
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
                            "id": "mgdzvt8zc7dbff6gt09nz4qfx",
                            "number": "KY23092702", # 线路编号
                            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
                            "endpoint_z": "海淀区后厂村路55号北京气象卫星地面站，球形建筑，1层机房，林茂伟13810802009，光缆施工联系闫振宇 13811904589",
                            "bandwidth": null, # 带宽（Mbs）
                            "task_description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）", # 用途描述
                            "line_type": "科技云科技专线", # 线路类型
                            "task_person": "周建虎", # 商务对接
                            "build_person": "胡亮亮、王振伟", # 线路搭建
                            "task_status": "normal" # 业务状态 normal(正常) deleted(删除)
                        }
                    ]
                }

        """
        return LinkHandler.list_link(view=self, request=request)
    
    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个链路'),
        deprecated=True,
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个链路

            http Code 200 Ok:
                {
                    "id": "t1hgf0ngc901dop1w6f8njo1w",
                    "number": "KY23092702",
                    "user": "空天院-中国遥感卫星地面站",
                    "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
                    "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
                    "bandwidth": null,
                    "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
                    "line_type": "科技云科技专线",
                    "business_person": "周建虎",
                    "build_person": "胡亮亮、王振伟",
                    "link_status": "using",
                    "remarks": "adaeda",
                    "enable_date": "2014-07-01",
                    "link_element": [
                        {
                            "index": 1,
                            "sub_index": 1,
                            "element_data": {
                                "type": "port",
                                "lease": null,
                                "port": {
                                    "is_linked": true,
                                    "element_id": "oethtqhyhfdmzsdj4yp0ev8ah",
                                    "link_id": [
                                        "t1hgf0ngc901dop1w6f8njo1w"
                                    ],
                                    "id": "oeth9k0527bmyrobqx2rng9xx",
                                    "number": "B8机柜29至31U_96芯ODF(1,13)",
                                    "row": 1,
                                    "col": 13,
                                    "distribution_frame": {
                                        "id": "oepwz6rs6p102ihz06jvxa9on",
                                        "number": "B8机柜29至31U_96芯ODF"
                                    }
                                },
                                "fiber": null,
                                "box": null
                            }
                        },
                        {
                            "index": 1,
                            "sub_index": 2,
                            "element_data": {
                                "type": "port",
                                "lease": null,
                                "port": {
                                    "is_linked": true,
                                    "element_id": "oetqqgftfnz5onyfqn9wtb54x",
                                    "link_id": [
                                        "t1hgf0ngc901dop1w6f8njo1w"
                                    ],
                                    "id": "oetqad25gdyqf8hk609wj36th",
                                    "number": "B8机柜29至31U_96芯ODF(1,14)",
                                    "row": 1,
                                    "col": 14,
                                    "distribution_frame": {
                                        "id": "oepwz6rs6p102ihz06jvxa9on",
                                        "number": "B8机柜29至31U_96芯ODF"
                                    }
                                },
                                "fiber": null,
                                "box": null
                            }
                        },
                        {
                            "index": 2,
                            "sub_index": 1,
                            "element_data": {
                                "type": "port",
                                "lease": null,
                                "port": {
                                    "is_linked": true,
                                    "element_id": "of1c3g2r8zoaqrj6huuruza3x",
                                    "link_id": [
                                        "t1hgf0ngc901dop1w6f8njo1w"
                                    ],
                                    "id": "of1bu33xhwh02f5pyezko1kt7",
                                    "number": "A3机柜31至33U_ODF7(1,13)",
                                    "row": 1,
                                    "col": 13,
                                    "distribution_frame": {
                                        "id": "oezopnz9w25dpx8wssox70h0c",
                                        "number": "A3机柜31至33U_ODF7"
                                    }
                                },
                                "fiber": null,
                                "box": null
                            }
                        },
                        {
                            "index": 2,
                            "sub_index": 2,
                            "element_data": {
                                "type": "port",
                                "lease": null,
                                "port": {
                                    "is_linked": true,
                                    "element_id": "of1ghrkokycspup1fpx0khbcc",
                                    "link_id": [
                                        "t1hgf0ngc901dop1w6f8njo1w"
                                    ],
                                    "id": "of1g86brvubspbtxr6mdpac62",
                                    "number": "A3机柜31至33U_ODF7(1,14)",
                                    "row": 1,
                                    "col": 14,
                                    "distribution_frame": {
                                        "id": "oezopnz9w25dpx8wssox70h0c",
                                        "number": "A3机柜31至33U_ODF7"
                                    }
                                },
                                "fiber": null,
                                "box": null
                            }
                        }
                    ]
                }
        """
        return LinkHandler.retrieve_link(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建链路'),
        deprecated=True,
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        列举链路信息

            http Code 200 Ok:
                {
                    "link_id": "t1hgf0ngc901dop1w6f8njo1w",
                }

        """

        return LinkHandler.creat_link(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'create':
            return CreatLinkSerializer
        return LinkSerializer
