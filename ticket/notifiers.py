from users import managers as user_manager
from users.models import Email
from core import taskqueue
from .models import Ticket, FollowUp


class TicketEmailNotifier:
    @staticmethod
    def thread_send_email(subject: str, receivers: list, message: str):
        email = Email.send_email(
            subject=subject, receivers=receivers, message=message, save_db=False, tag=Email.Tag.TICKET.value)
        return email

    @staticmethod
    def new_ticket_notice(ticket: Ticket):
        user_qs = user_manager.filter_user_queryset(is_federal_admin=True)
        receivers = [u.username for u in user_qs]
        message = f"""
你好：

用户 {ticket.username} 新提交了一个工单。

工单标题为:
  {ticket.title}

工单问题描述：
  {ticket.description}


祝好
中国科技云一体化云服务平台(https://service.cstcloud.cn)
        """
        future = taskqueue.submit_task(
            TicketEmailNotifier.thread_send_email,
            kwargs={
                'subject': '新工单提交通知', 'receivers': receivers, 'message': message
            }
        )
        return future

    @staticmethod
    def new_followup_notice(receivers: list, ticket: Ticket, folowup: FollowUp):
        message = f"""
你好：

工单有了新的动态，用户 {ticket.username} 回复了工单。

工单标题为:
  {ticket.title}

工单问题描述：
  {ticket.description}

回复内容：
  {folowup.comment}


祝好
中国科技云一体化云服务平台(https://service.cstcloud.cn)
            """
        future = taskqueue.submit_task(
            TicketEmailNotifier.thread_send_email,
            kwargs={
                'subject': '工单跟进动态通知', 'receivers': receivers, 'message': message
            }
        )
        return future
