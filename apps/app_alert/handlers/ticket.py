from apps.app_alert.models import AlertService
from apps.app_alert.models import AlertModel
from apps.app_alert.models import AlertAbstractModel
from apps.app_alert.models import ServiceLog
from apps.app_alert.models import ServiceMetric
from apps.app_alert.utils import errors
from apps.app_alert.utils.utils import DateUtils
from apps.app_alert.models import AlertTicket
from apps.app_alert.handlers.handlers import move_to_resolved
from apps.app_alert.models import TicketHandler
from django.db import transaction
from apps.app_alert.serializers import TicketCustomSerializer
from apps.app_alert.serializers import TicketUpdateHandlersSerializer
from rest_framework.exceptions import PermissionDenied


def has_service_permission(service_name, user):
    if user.is_superuser:
        return True
    service = AlertService.objects.filter(name_en=service_name).first()
    if not service:
        raise errors.InvalidArgument('invalid service')

    service_user = service.users.filter(username=user.username)
    if service_user:
        return True


class TicketManager(object):
    def __init__(self, request):
        self.request = request

    def create_ticket(self, serializer):
        with transaction.atomic():
            self._create_ticket(serializer)

    def update_ticket(self, serializer):
        self._update_ticket(serializer)

    def _create_ticket(self, serializer):
        custom_serializer = TicketCustomSerializer(data=self.request.data)
        custom_serializer.is_valid(raise_exception=True)
        service = custom_serializer.data.get('service')
        # 用户权限验证
        if not has_service_permission(service_name=service, user=self.request.user):
            raise PermissionDenied()
        # 告警是否已经存在工单
        alert_object_list = list()
        for alert in self.request.data.get('alerts'):
            obj = AlertModel.objects.filter(id=alert).first()
            if not obj:
                raise errors.InvalidArgument(f'invalid alert:{alert}')
            if obj.ticket:
                raise errors.InvalidArgument(f'alert ticket already exists')
            alert_object_list.append(obj)
        # 保存工单
        ticket = serializer.save(
            submitter=self.request.user,
            service=service,
        )
        # 告警关联工单
        for obj in alert_object_list:
            obj.ticket = ticket
            obj.save()
            if ticket.resolution:  # 已经填写解决方案
                obj.recovery = DateUtils.timestamp()
                obj.status = AlertModel.AlertStatus.RESOLVED.value
                ticket.status = AlertTicket.Status.CLOSED.value
                ticket.save()
                obj.save()
                if obj.type == AlertModel.AlertType.LOG.value:  # 日志类 归入 已恢复队列
                    move_to_resolved(obj)

        # 关联处理人
        handlers = custom_serializer.data.get('handlers')
        for user in handlers:
            TicketHandler.objects.create(
                ticket=ticket,
                user=user,
            )

    def _update_ticket(self, serializer):
        custom_serializer = TicketUpdateHandlersSerializer(data=self.request.data)
        custom_serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        target_handlers = custom_serializer.data.get('handlers')
        preview_handlers = TicketHandler.objects.filter(ticket=ticket).all()

        # 判断是否有移除的处理人
        for handler in preview_handlers:
            if handler.user in target_handlers:
                continue
            handler.delete()  # 移除

        for user in target_handlers:
            if TicketHandler.objects.filter(ticket=ticket, user=user).first():
                continue
            TicketHandler.objects.create(ticket=ticket, user=user)
