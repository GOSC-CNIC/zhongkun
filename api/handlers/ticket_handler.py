from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors as exceptions
from api.viewsets import AsRoleGenericViewSet
from api.serializers import ticket as ticket_serializers
from ticket.models import Ticket, TicketChange
from ticket.managers import TicketManager

from .handlers import serializer_error_msg


class TicketHandler:
    @staticmethod
    def create_ticket(view: AsRoleGenericViewSet, request, kwargs):
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

    @staticmethod
    def update_ticket(view: AsRoleGenericViewSet, request, kwargs):
        ticket_id = kwargs[view.lookup_field]

        try:
            params = TicketHandler._ticket_create_validate_params(view=view, request=request)
            ticket = TicketManager.get_ticket(ticket_id=ticket_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        new_title = params['title']
        new_description = params['description']
        new_service_type = params['service_type']
        new_contact = params['contact']

        if ticket.submitter_id != request.user.id:
            return view.exception_response(exceptions.AccessDenied(message='你没有此工单的访问权限'))

        if ticket.status not in [Ticket.Status.OPEN.value, Ticket.Status.PROGRESS.value]:
            return view.exception_response(exceptions.ConflictTicketStatus(message='只允许更改状态为“打开”和“处理中”的工单'))

        no_changes = all([
            new_title == ticket.title,
            new_description == ticket.description,
            new_service_type == ticket.service_type,
            new_contact == ticket.contact
        ])
        if no_changes:
            return Response(data=ticket_serializers.TicketSerializer(instance=ticket).data)

        update_fields = []
        ticket_chenges = []
        if new_title != ticket.title:
            update_fields.append('title')
            ticket_chenges.append([TicketChange.TicketField.TITLE.value, ticket.title, new_title])
            ticket.title = new_title

        if new_description != ticket.description:
            update_fields.append('description')
            ticket_chenges.append([TicketChange.TicketField.DESCRIPTION.value, ticket.description, new_description])
            ticket.description = new_description

        if new_service_type != ticket.service_type:
            update_fields.append('service_type')
            ticket.service_type = new_service_type

        if new_contact != ticket.contact:
            update_fields.append('contact')
            ticket.contact = new_contact

        try:
            ticket.save(update_fields=update_fields)
            # open状态的工单更改不产生 更改记录
            if ticket.status != Ticket.Status.OPEN.value and ticket_chenges:
                for field, old_value, new_value in ticket_chenges:
                    TicketManager.create_followup_action(
                        user=request.user, ticket_id=ticket.id, field_name=field,
                        old_value=old_value, new_value=new_value, atomic=False
                    )
        except Exception as exc:
            return view.exception_response(exceptions.Error(message=_('更改工单失败。') + str(exc)))

        return Response(data=ticket_serializers.TicketSerializer(instance=ticket).data)

    @staticmethod
    def list_tickets(view: AsRoleGenericViewSet, request, kwargs):
        try:
            params = TicketHandler._list_tickets_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        user = request.user
        has_role = params['has_role']
        role = params['role']
        if has_role:
            if role == view.AS_ROLE_ADMIN and user.is_federal_admin():
                queryset = TicketManager().get_tickets_queryset(
                    submitter_id=params['submitter_id'], status=params['status'],
                    service_type=params['service_type'], severity=params['severity']
                )
            else:
                return view.exception_response(exceptions.AccessDenied(message='你没有联邦管理员权限'))
        else:
            queryset = TicketManager().get_user_tickets_queryset(
                user=user, status=params['status'],
                service_type=params['service_type'], severity=params['severity']
            )

        try:
            tickets = view.paginate_queryset(queryset=queryset)
            serializer = view.get_serializer(tickets, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_tickets_validate_params(view: AsRoleGenericViewSet, request):
        """
        :raises: Error
        """
        status_ = request.query_params.get('status', None)
        service_type = request.query_params.get('service_type', None)
        submitter_id = request.query_params.get('submitter_id', None)
        severity = request.query_params.get('severity', None)

        if status_ is not None and status_ not in Ticket.Status.values:
            raise exceptions.InvalidArgument(message=_('指定的工单状态无效'), code='InvalidStatus')

        if service_type is not None and service_type not in Ticket.ServiceType.values:
            raise exceptions.InvalidArgument(message=_('指定的相关服务类型无效'), code='InvalidServiceType')

        if severity is not None and severity not in Ticket.Severity.values:
            raise exceptions.InvalidArgument(message=_('指定的问题严重程度值无效'), code='InvalidSeverity')

        has_role, role = view.check_as_role_request(request=request)
        if submitter_id is not None and not has_role:
            raise exceptions.ParameterConflict(
                message=_('查询指定提交人的工单参数“submitter_id”，只允许与参数“as_role”一起提交。'))

        return {
            'status': status_,
            'service_type': service_type,
            'severity': severity,
            'submitter_id': submitter_id,
            'has_role': has_role,
            'role': role
        }

    @staticmethod
    def ticket_detial(view: AsRoleGenericViewSet, request, kwargs):
        ticket_id = kwargs[view.lookup_field]
        try:
            has_role, role = view.check_as_role_request(request=request)
            ticket = TicketManager.get_ticket(ticket_id=ticket_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        user = request.user
        if has_role:
            if role == view.AS_ROLE_ADMIN and user.is_federal_admin():
                pass
            else:
                return view.exception_response(exceptions.AccessDenied(message='你没有联邦管理员权限'))
        elif ticket.submitter_id != request.user.id:
            return view.exception_response(exceptions.AccessDenied(message='你没有此工单的访问权限'))

        try:
            serializer = view.get_serializer(instance=ticket)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)
