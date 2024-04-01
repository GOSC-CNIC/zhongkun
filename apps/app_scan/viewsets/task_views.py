from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from django.utils.translation import gettext_lazy

from api.paginations import ScanTaskPageNumberPagination
from api.viewsets import CustomGenericViewSet
from apps.app_scan.models import VtTask
from apps.app_scan.handlers.task_handler import TaskHandler
from apps.app_scan.serializers import ScanTaskOrderCreateSerializer, ScanTaskListSerializer


class ScanTaskViewSet(CustomGenericViewSet):
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = ScanTaskPageNumberPagination
    lookup_field = "id"

    @swagger_auto_schema(
        operation_summary=gettext_lazy("列举用户漏扫任务"),
        manual_parameters=[
            openapi.Parameter(
                name="type",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f"扫描类型筛选，{VtTask.TaskType.values}",
                enum=VtTask.TaskType.values
            )
        ],
        responses={200: ""},
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户站点扫描任务和主机扫描任务

            Http Code: 状态码200，返回数据：
            {
              "count": 5,
              "page_num": 3,
              "page_size": 2,
              "results": [
                {
                  "id": "727cee5a-9f70-11ed-aba9-c8009fe2ebbc",
                  "name": "name-string",
                  "type": "web",
                  "target": "https://baidu.com:8888/",
                  "task_status": "queued",
                  "remark": "string",
                  "creation": "2023-01-29T01:01:22.403887Z",
                  "modification": "2023-01-29T01:01:00Z",
                  "user": {     #关联用户属于用户的监控任务
                    "id": "1",
                    "username": "shun"
                  },
                }
              ]
            }
            http code 400:
            {
                "code": "xxx",
                "message": "xxx"
            }
            400：
                InvalidArgument：指定扫描类型无效

        """
        return TaskHandler.list_scan_task(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy("创建一个网站或主机扫描任务"),
        manual_parameters=[],
        responses={200: ""},
    )
    def create(self, request, *args, **kwargs):
        """
        创建安全扫描任务

            Http Code: 状态码200，返回数据：
            {
                "order_id": "xxx"
            }
            
            http code 400、404、409:
            {
                "code": "xxx",
                "message": "xxx"
            }
            400：
                BadRequest：
                InvalidScheme：协议无效
                InvalidHostname：域名无效
                InvalidUri：路径无效
                InvalidIp：ip无效
                InvalidScanType：扫描方式指定无效
                InvalidUrl：url无效
            404：
                NotFound：安全扫描服务信息不存在
            409：
                ConflictError：
                ServiceNoPayAppServiceId：未配置对应结算系统APP服务id

        """
        return TaskHandler.create_scan_task_order(view=self, request=request)

    def get_serializer_class(self):
        if self.action in ["create"]:
            return ScanTaskOrderCreateSerializer
        if self.action in ["list"]:
            return ScanTaskListSerializer
        return Serializer
