from api.viewsets import NormalGenericViewSet
from django.utils.translation import gettext_lazy, gettext as _
from api.paginations import NewPageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from link.handlers.task_handler import TaskHandler
from link.serializers.task_serializer import TaskSerializer
from rest_framework.decorators import action


class TaskViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举业务'),
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举业务信息

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
        return TaskHandler.list_task(view=self, request=request)
    

    def get_serializer_class(self):
        return TaskSerializer
