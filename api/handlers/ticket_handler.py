from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors as exceptions
from api.viewsets import NormalGenericViewSet
from api.serializers import ticket as ticket_serializers
from ticket.models import Ticket
from ticket.managers import TicketManager

from .handlers import serializer_error_msg


class TicketHandler:
    @staticmethod
    def create_ticket(view: NormalGenericViewSet, request, kwargs):
        try:
            params = TicketHandler._ticket_create_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        title = params['title']
        description = params['description']
        service_type = params['service_type']
        contact = params['contact']
        user = request.user

        count = TicketManager.not_result_ticket_count(user_id=user.id)
        if count >= 5:
            return view.exception_response(exceptions.TooManyTicket())

        try:
            ticket = TicketManager.create_ticket(
                title=title, description=description, service_type=service_type, contact=contact, submitter=user
            )
        except Exception as exc:
            return view.exception_response(exceptions.Error(message=_('创建工单错误。') + str(exc)))

        return Response(data=ticket_serializers.TicketSerializer(instance=ticket).data)

    @staticmethod
    def _ticket_create_validate_params(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'title' in s_errors:
                exc = exceptions.BadRequest(message=_('无效的标题。') + s_errors['title'][0], code='InvalidTitle')
            elif 'description' in s_errors:
                exc = exceptions.BadRequest(
                    message=_('无效的问题描述。') + s_errors['description'][0], code='InvalidDescription')
            elif 'service_type' in s_errors:
                exc = exceptions.BadRequest(
                    message=_('问题相关的服务无效。') + s_errors['service_type'][0], code='InvalidServiceType')
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = exceptions.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data
        title = data['title']
        description = data['description']
        service_type = data['service_type']

        if len(title) < 10:
            raise exceptions.BadRequest(message=_('标题长度不能少于10个字符'), code='InvalidTitle')
        elif len(description) < 10:
            raise exceptions.BadRequest(message=_('问题描述不能少于10个字符'), code='InvalidDescription')
        elif service_type not in Ticket.ServiceType.values:
            raise exceptions.BadRequest(message=_('问题相关的服务无效'), code='InvalidServiceType')

        return data

