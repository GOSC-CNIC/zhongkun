from django.db import transaction
from django.utils.translation import gettext as _

from core import errors
from .models import Ticket, FollowUp, TicketChange, TicketRating


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
        nr_status = [Ticket.Status.OPEN.value, Ticket.Status.PROGRESS.value]
        return Ticket.objects.filter(submitter_id=user_id, status__in=nr_status).count()

    @staticmethod
    def get_tickets_queryset(
            submitter_id: str = None,
            status: str = None,
            service_type: str = None,
            severity: str = None,
            assigned_to_id: str = None
    ):
        lookups = {}

        if assigned_to_id:
            lookups['assigned_to_id'] = assigned_to_id

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

    @staticmethod
    def get_followup_queryset():
        return FollowUp.objects.all()

    @staticmethod
    def get_ticket_followup_queryset(ticket_id: str, is_only_replay: bool = False):
        qs = FollowUp.objects.select_related('ticket_change').filter(ticket_id=ticket_id)
        if is_only_replay:
            qs = qs.filter(fu_type=FollowUp.FuType.REPLY.value)

        return qs

    @staticmethod
    def ticket_assigned_to_user(user, ticket, assigned_to):
        if ticket.assigned_to:
            old_username = ticket.assigned_to.username
        else:
            old_username = ''

        with transaction.atomic():
            fu = TicketManager.create_followup_action(
                user=user, ticket_id=ticket.id, field_name=TicketChange.TicketField.ASSIGNED_TO.value,
                old_value=old_username, new_value=assigned_to.username, atomic=False
            )

            update_fields = ['assigned_to_id']
            ticket.assigned_to_id = assigned_to.id
            if ticket.status == Ticket.Status.OPEN.value:
                ticket.status = Ticket.Status.PROGRESS.value
                update_fields.append('status')

            ticket.save(update_fields=update_fields)

        return ticket, fu

    @staticmethod
    def create_ticket_rating(ticket: Ticket, score: int, comment: str, user=None) -> TicketRating:
        """
        创建一个工单评价

        :param ticket: 工单
        :param score: 评分， 1-5
        :param comment: 评论
        :param user: 评论人；默认None时系统自动提交
        :return:
            TicketRating()

        :raises: Error
        """
        if ticket.status != Ticket.Status.CLOSED.value:
            raise errors.ConflictTicketStatus(message=_('只允许评价”已关闭“状态的工单。'))

        if score < 1 or score > 5:
            raise errors.BadRequest(message=_('评分只允许在1至5之间。'))

        if user:
            user_id = user.id
            username = user.username
            is_sys_submit = False
        else:
            user_id = ''
            username = ''
            is_sys_submit = True

        rating = TicketRating(
            ticket_id=ticket.id,
            score=score,
            comment=comment,
            user_id=user_id,
            username=username,
            is_sys_submit=is_sys_submit
        )
        rating.save(force_insert=True)
        return rating
