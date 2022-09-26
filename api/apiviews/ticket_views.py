from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import NormalGenericViewSet
from api.paginations import NewPageNumberPagination
from api.serializers import ticket as ticket_serializers
from api.handlers.ticket_handler import TicketHandler


class TicketViewSet(NormalGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('提交一个工单'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        提交一个工单

            http code 200：
            {
                "id": "202209260203353120246310",
                "title": "test 工单，我遇到一个问题",
                "description": "这里是问题的描述，不能少于10个字符",
                "status": "open",
                "service_type": "server",
                "severity": "normal",
                "submit_time": "2022-09-26T01:36:03.802351Z",
                "modified_time": "2022-09-26T01:36:03.802414Z",
                "contact": "string",
                "resolution": "",
                "submitter": {
                    "id": "1",
                    "username": "shun"
                },
                "assigned_to": null
            }

            http code 400, 409, 500:
            {
                "code": "InvalidTitle",
                "message": "标题长度不能少于10个字符"
            }
            400:
                InvalidTitle: 无效的标题 / 标题长度不能少于10个字符
                InvalidDescription: 无效的问题描述 / 问题描述不能少于10个字符
                InvalidServiceType: 问题相关的服务无效
            409:
                TooManyTicket: 您已提交了多个工单，待解决，暂不能提交更多的工单
            500:
                InternalError: 创建工单错误
        """
        return TicketHandler().create_ticket(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return ticket_serializers.TicketCreateSerializer

        return Serializer
