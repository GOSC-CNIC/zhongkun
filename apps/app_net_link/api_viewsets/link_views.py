from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.api.viewsets import NormalGenericViewSet
from apps.api.paginations import NewPageNumberPagination
from apps.app_net_link.handlers.link import LinkHandler
from apps.app_net_link import serializers as link_serializers
from apps.app_net_link.models import Link
from apps.app_net_link.permissions import LinkIPRestrictPermission


class LinkViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举链路'),
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
                            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）", # 用途描述
                            "line_type": "科技云科技专线", # 线路类型
                            "business_person": "周建虎", # 商务对接
                            "build_person": "胡亮亮、王振伟", # 线路搭建
                            "link_status": "idle", # using(使用); backup(备用); idle(闲置')
                            "remarks": "xx",
                            "enable_date": "2023-12-12" # 开通日期
                        }
                    ]
                }

        """
        return LinkHandler.list_link(view=self, request=request)
    
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
                                "port": {
                                    "is_linked": true,
                                    "element_id": "oethtqhyhfdmzsdj4yp0ev8ah",
                                    "link_id": [],
                                    "id": "oeth9k0527bmyrobqx2rng9xx",
                                    "number": "B8机柜29至31U_96芯ODF(1,13)",
                                    "row": 1,
                                    "col": 13,
                                    "distribution_frame": {
                                        "id": "oepwz6rs6p102ihz06jvxa9on",
                                        "number": "B8机柜29至31U_96芯ODF"
                                    }
                                },
                            }
                        },
                        {
                            "index": 2,
                            "sub_index": 2,
                            "element_data": {
                                "type": "fiber",
                                "fiber": {
                                    "is_linked": true,
                                    "element_id": "86gnebw3kbdnk4haqgr6fu38y",
                                    "link_id": [],
                                    "id": "891jxdtcmf97myyi71qc360bu",
                                    "sequence": 2,
                                    "fiber_cable": {
                                        "id": "rkxi2xn7otatg834z968ww83t",
                                        "number": "光缆-天空院"
                                    }
                                }
                            }
                        }
                    ]
                }
        """
        return LinkHandler.retrieve_link(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建链路'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建链路

            http Code 200 Ok:
                {
                    "link_id": "t1hgf0ngc901dop1w6f8njo1w",
                }
        """

        return LinkHandler.creat_link(view=self, request=request)

    def get_serializer_class(self):
        if self.action in 'list':
            return link_serializers.LinkSerializer
        elif self.action in 'create':
            return link_serializers.CreatLinkSerializer

        return Serializer
