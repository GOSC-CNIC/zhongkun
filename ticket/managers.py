
from .models import Ticket


class TicketManager:
    @staticmethod
    def get_queryset():
        return Ticket.objects.all()

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
