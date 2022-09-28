from django.db import transaction

from core import errors
from .models import Ticket, FollowUp, TicketChange


class TicketManager:
    @staticmethod
    def get_queryset():
        return Ticket.objects.all()

    @staticmethod
    def get_ticket(ticket_id: str):
        """
        :raises: TicketNotExist
        """
        ticket = Ticket.objects.select_related('submitter', 'assigned_to').filter(id=ticket_id).first()
        if ticket is None:
            raise errors.TicketNotExist()

        return ticket

    @staticmethod
    def create_ticket(
            title: str,
            description: str,
            service_type: str,
            contact: str,
            submitter
    ) -> Ticket:
        ticket = Ticket(
            title=title,
            description=description,
            service_type=service_type,
            contact=contact,
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=submitter,
            username=submitter.username
        )
        ticket.save(force_insert=True)
        return ticket

    @staticmethod
    def not_result_ticket_count(user_id: str) -> int:
        """
        用户提交的未解决的工单的数量
        """
        nr_status = [Ticket.Status.OPEN.value, Ticket.Status.PROGRESS.value, Ticket.Status.REOPENED.value]
        return Ticket.objects.filter(submitter_id=user_id, status__in=nr_status).count()

    @staticmethod
    def get_tickets_queryset(
            submitter_id: str = None,
            status: str = None,
            service_type: str = None,
            severity: str = None
    ):
        lookups = {}

        if submitter_id:
            lookups['submitter_id'] = submitter_id

        if status:
            lookups['status'] = status

        if service_type:
            lookups['service_type'] = service_type

        if severity:
            lookups['severity'] = severity

        return Ticket.objects.select_related('submitter', 'assigned_to').filter(**lookups).order_by('-submit_time')

    def get_user_tickets_queryset(self, user, status: str = None, service_type: str = None, severity: str = None):
        return self.get_tickets_queryset(
            submitter_id=user.id, status=status, service_type=service_type, severity=severity
        )

    @staticmethod
    def create_followup_action(user, ticket_id: str, field_name: str, old_value: str, new_value: str, atomic: bool = True):
        """
        工单更改记录 跟进动态  事务 原子操作
        """
        if not atomic:
            return TicketManager._create_followup_action(
                user=user, ticket_id=ticket_id, field_name=field_name, old_value=old_value, new_value=new_value
            )

        with transaction.atomic():
            return TicketManager._create_followup_action(
                user=user, ticket_id=ticket_id, field_name=field_name, old_value=old_value, new_value=new_value
            )

    @staticmethod
    def _create_followup_action(user, ticket_id: str, field_name: str, old_value: str, new_value: str):
        tc = TicketChange(
            ticket_field=field_name, old_value=old_value, new_value=new_value
        )
        tc.save(force_insert=True)
        title = tc.display
        if len(title) > 250:
            title = title[:250]

        fu = FollowUp(
            ticket_id=ticket_id,
            fu_type=FollowUp.FuType.ACTION.value,
            title=title,
            user_id=user.id,
            ticket_change=tc
        )
        fu.save(force_insert=True)
        return fu

    @staticmethod
    def create_followup_reply(user, ticket_id: str, comment: str):
        """
        添加工单跟进动态
        """
        fu = FollowUp(
            ticket_id=ticket_id,
            fu_type=FollowUp.FuType.REPLY.value,
            title='',
            comment=comment,
            user_id=user.id,
            ticket_change=None
        )
        fu.save(force_insert=True)
        return fu
