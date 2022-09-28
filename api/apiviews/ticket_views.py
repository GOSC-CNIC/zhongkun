from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import AsRoleGenericViewSet
from api.paginations import NewPageNumberPagination
from api.serializers import ticket as ticket_serializers
from api.handlers.ticket_handler import TicketHandler
from ticket.models import Ticket


class TicketViewSet(AsRoleGenericViewSet):

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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举工单'),
        manual_parameters=[
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('筛选指定状态的工单')
            ),
            openapi.Parameter(
                name='service_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('筛选指定相关服务的工单。') + f'{Ticket.ServiceType.choices}'
            ),
            openapi.Parameter(
                name='severity',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('问题严重程度。') + f'{Ticket.Severity.choices}'
            ),
            openapi.Parameter(
                name='submitter_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('筛选提交人的工单，只能和参数“as_role”一起提交。')
            ),
        ] + AsRoleGenericViewSet.PARAMETERS_AS_ROLE,
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举工单

            http code 200：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "id": "202209260136038015666375",
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
              ]
            }

            http code 400, 403, 500:
            {
                "code": "InvalidStatus",
                "message": "指定的工单状态无效"
            }
            400:
                InvalidStatus: 指定的工单状态无效
                ParameterConflict: 查询指定提交人的工单参数“submitter_id”，只允许与参数“as_role”一起提交。
                InvalidServiceType: 问题相关的服务无效
                InvalidAsRole: 指定的身份无效
                InvalidSeverity: 指定的问题严重程度值无效
            403:
                AccessDenied: 你没有联邦管理员权限
            500:
                InternalError: 创建工单错误
        """
        return TicketHandler().list_tickets(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个工单详情'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个工单详情

            http code 200：
            {
                "id": "202209260203353120246310",
                "title": "test 工单，我遇到一个问题",
                "description": "这里是问题的描述，不能少于10个字符",
                "status": "progress",
                "service_type": "server",
                "severity": "normal",
                "submit_time": "2022-09-26T01:36:03.802351Z",
                "modified_time": "2022-09-26T01:36:03.802414Z",
                "contact": "string",
                "resolution": "",
                "submitter": {
                    "id": "xxx",
                    "username": "shun"
                },
                "assigned_to": {
                    "id": "xxx",
                    "username": "test"
                }
            }

            http code 400, 403, 404, 500:
            {
                "code": "TicketNotExist",
                "message": "工单不存在"
            }
            400:
                InvalidAsRole: 指定的身份无效
            403:
                AccessDenied: 你没有联邦管理员权限 / 你没有此工单的访问权限
            404:
                TicketNotExist: 工单不存在
            500:
                InternalError: 查询工单错误
        """
        return TicketHandler().ticket_detial(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('更改一个工单'),
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='update', url_name='update-ticket')
    def update_ticket(self, request, *args, **kwargs):
        """
        更改一个工单

            * 只允许工单提交人修改 “打开”和“处理中”的工单

            http code 200：
            {
                "id": "202209260203353120246310",
                "title": "test 工单，我遇到一个问题",
                "description": "这里是问题的描述，不能少于10个字符",
                "status": "progress",
                "service_type": "server",
                "severity": "normal",
                "submit_time": "2022-09-26T01:36:03.802351Z",
                "modified_time": "2022-09-26T01:36:03.802414Z",
                "contact": "string",
                "resolution": "",
                "submitter": {
                    "id": "f5d705da-3eca-11ed-af4e-c8009fe2ebbc",
                    "username": "shun"
                },
                "assigned_to": {
                    "id": "f5d705da-3eca-11ed-af4e-c8009fe2ebbc",
                    "username": "test"
                }
            }

            http code 400, 403, 404, 409, 500:
            {
                "code": "TicketNotExist",
                "message": "工单不存在"
            }
            400:
                InvalidTitle: 无效的标题 / 标题长度不能少于10个字符
                InvalidDescription: 无效的问题描述 / 问题描述不能少于10个字符
                InvalidServiceType: 问题相关的服务无效
            403:
                AccessDenied: 你没有此工单的访问权限
            404:
                TicketNotExist: 工单不存在
            409:
                ConflictTicketStatus: 只允许更改状态为“打开”和“处理中”的工单
            500:
                InternalError: 更改工单错误
        """
        return TicketHandler().update_ticket(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('更改一个工单的严重程度'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='severity',
                in_=openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('工单严重程度。') + f'{Ticket.Severity.choices}'
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path=r'severity/(?P<severity>[^/]+)', url_name='ticket-severity-change')
    def ticket_severity_change(self, request, *args, **kwargs):
        """
        更改一个工单的严重程度

            * 只允许联邦管理员修改工单的严重程度

            http code 200：
            {
                "severity": "xxx"
            }

            http code 400, 403, 404, 500:
            {
                "code": "TicketNotExist",
                "message": "工单不存在"
            }
            400:
                InvalidSeverity: 指定的工单严重程度无效
            403:
                AccessDenied: 你没有此工单的访问权限
            404:
                TicketNotExist: 工单不存在
            500:
                InternalError: 更改工单错误
        """
        return TicketHandler().ticket_severity_change(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('更改一个工单的状态'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='status',
                in_=openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('工单状态。') + f'{Ticket.Status.choices}'
            ),
        ] + AsRoleGenericViewSet.PARAMETERS_AS_ROLE,
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path=r'status/(?P<status>[^/]+)', url_name='ticket-status-change')
    def ticket_status_change(self, request, *args, **kwargs):
        """
        更改一个工单的状态

            * 工单提交人只允许更改 canceled和open的状态；
                open -> canceled;
                canceled -> open ;
            * 联邦管理员 允许更改 除 canceled之外的状态；

            http code 200：
            {
                "status": "xxx"
            }

            http code 400, 403, 404, 409, 500:
            {
                "code": "TicketNotExist",
                "message": "工单不存在"
            }
            400:
                InvalidAsRole: 指定的身份无效
                InvalidStatus: 指定的工单状态无效
            403:
                AccessDenied: 你没有此工单的访问权限
            404:
                TicketNotExist: 工单不存在
            409:
                ConflictTicketStatus: 不允许（无权限）更改当前状态下的工单状态 / 不允许（无权限）把工单的状态更改为指定的状态
            500:
                InternalError: 更改工单错误
        """
        return TicketHandler().ticket_status_change(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['create', 'update_ticket']:
            return ticket_serializers.TicketCreateSerializer
        elif self.action in ['list', 'retrieve']:
            return ticket_serializers.TicketSerializer

        return Serializer
