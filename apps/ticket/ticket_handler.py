from django.utils.translation import gettext as _
from django.db import transaction
from rest_framework.response import Response

from core import errors as exceptions
from api.viewsets import AsRoleGenericViewSet, serializer_error_msg
from api.paginations import FollowUpMarkerCursorPagination
from ticket.models import Ticket, TicketChange, TicketRating
from ticket.managers import TicketManager
from ticket.notifiers import TicketEmailNotifier
from ticket import serializers as ticket_serializers
from users.managers import get_user_by_name


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

        try:
            TicketEmailNotifier.new_ticket_notice(ticket=ticket)
        except Exception as exc:
            pass

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
            return view.exception_response(exceptions.AccessDenied(message=_('你没有此工单的访问权限')))

        if ticket.status not in [Ticket.Status.OPEN.value, Ticket.Status.PROGRESS.value]:
            return view.exception_response(
                exceptions.ConflictTicketStatus(message=_('只允许更改状态为“打开”和“处理中”的工单')))

        no_changes = all([
            new_title == ticket.title,
            new_description == ticket.description,
            new_service_type == ticket.service_type,
            new_contact == ticket.contact
        ])
        if no_changes:
            return Response(data=ticket_serializers.TicketSerializer(instance=ticket).data)

        update_fields = ['modified_time']
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
            with transaction.atomic():
                ticket.save(update_fields=update_fields)
                # open状态的工单（已指派处理人的工单除外）更改不产生 更改记录
                if (ticket.status != Ticket.Status.OPEN.value or ticket.assigned_to_id) and ticket_chenges:
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
                    service_type=params['service_type'], severity=params['severity'],
                    assigned_to_id=params['assigned_to_user_id']
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
        assigned_to = request.query_params.get('assigned_to', None)

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

        if assigned_to is not None:
            if not has_role:
                raise exceptions.ParameterConflict(
                    message=_('查询分配给自己的工单参数“assigned_to”，只允许与参数“as_role”一起提交。'))

            if assigned_to:
                if assigned_to == request.user.username:
                    assigned_to_user_id = request.user.id
                else:   # UserNotExist
                    user = get_user_by_name(username=assigned_to)
                    assigned_to_user_id = user.id
            else:       # 值为空时，查询自己
                assigned_to_user_id = request.user.id
        else:
            assigned_to_user_id = None

        return {
            'status': status_,
            'service_type': service_type,
            'severity': severity,
            'submitter_id': submitter_id,
            'has_role': has_role,
            'role': role,
            'assigned_to_user_id': assigned_to_user_id
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
                return view.exception_response(exceptions.AccessDenied(message=_('你没有联邦管理员权限')))
        elif ticket.submitter_id != request.user.id:
            return view.exception_response(exceptions.AccessDenied(message=_('你没有此工单的访问权限')))

        try:
            serializer = view.get_serializer(instance=ticket)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def ticket_severity_change(view: AsRoleGenericViewSet, request, kwargs):
        ticket_id = kwargs[view.lookup_field]
        new_severity = kwargs.get('severity', '')

        if new_severity not in Ticket.Severity.values:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('指定的工单严重程度无效。'), code='InvalidSeverity'))

        if not request.user.is_federal_admin():
            return view.exception_response(exceptions.AccessDenied(message=_('你没有此工单的访问权限。')))

        try:
            ticket = TicketManager.get_ticket(ticket_id=ticket_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if ticket.assigned_to_id != request.user.id:
            return view.exception_response(exceptions.AccessDenied(message=_('你不是此工单的指派处理人。')))

        if ticket.status == Ticket.Status.CLOSED.value:
            return view.exception_response(exceptions.ConflictTicketStatus(message=_('工单已关闭。')))

        if new_severity == ticket.severity:
            return Response(data={'severity': new_severity})

        try:
            with transaction.atomic():
                old_severity = ticket.severity
                ticket.severity = new_severity
                ticket.save(update_fields=['severity', 'modified_time'])
                TicketManager.create_followup_action(
                    user=request.user, ticket_id=ticket.id,
                    field_name=TicketChange.TicketField.SEVERITY.value,
                    old_value=old_severity, new_value=new_severity, atomic=False
                )
        except Exception as exc:
            return view.exception_response(exceptions.Error(message=_('更改工单严重程度失败。') + str(exc)))

        return Response(data={'severity': new_severity})

    @staticmethod
    def ticket_status_change(view: AsRoleGenericViewSet, request, kwargs):
        ticket_id = kwargs[view.lookup_field]
        new_status = kwargs.get('status', '')

        if new_status not in Ticket.Status.values:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('指定的工单状态无效。'), code='InvalidStatus'))

        try:
            has_role, role = view.check_as_role_request(request=request)
            ticket = TicketManager.get_ticket(ticket_id=ticket_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if ticket.status == Ticket.Status.CLOSED.value:
            return view.exception_response(
                exceptions.ConflictTicketStatus(message=_('您不允许更改“已关闭”状态的工单。')))

        user = request.user
        if has_role:
            if role == view.AS_ROLE_ADMIN and user.is_federal_admin():
                if ticket.assigned_to_id != request.user.id:
                    return view.exception_response(exceptions.AccessDenied(message=_('你不是此工单的指派处理人。')))
            else:
                return view.exception_response(exceptions.AccessDenied(message=_('你没有联邦管理员权限')))
        else:
            if ticket.submitter_id != request.user.id:
                return view.exception_response(exceptions.AccessDenied(message=_('你没有此工单的访问权限')))

            if new_status != Ticket.Status.CLOSED.value:
                return view.exception_response(
                    exceptions.ConflictTicketStatus(message=_('您只允许关闭工单。')))

        if new_status == ticket.status:
            return Response(data={'status': new_status})

        try:
            with transaction.atomic():
                old_status = ticket.status
                ticket.status = new_status
                ticket.save(update_fields=['status', 'modified_time'])
                TicketManager.create_followup_action(
                    user=request.user, ticket_id=ticket.id,
                    field_name=TicketChange.TicketField.STATUS.value,
                    old_value=old_status, new_value=new_status, atomic=False
                )
        except Exception as exc:
            return view.exception_response(exceptions.Error(message=_('更改工单状态失败。') + str(exc)))

        return Response(data={'status': new_status})

    @staticmethod
    def add_followup(view: AsRoleGenericViewSet, request, kwargs):
        ticket_id = kwargs[view.lookup_field]
        try:
            params = TicketHandler._add_followup_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            has_role, role = view.check_as_role_request(request=request)
            ticket = TicketManager.get_ticket(ticket_id=ticket_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        comment = params['comment']
        user = request.user
        if has_role:
            if role == view.AS_ROLE_ADMIN and user.is_federal_admin():
                if ticket.assigned_to_id != request.user.id:
                    return view.exception_response(exceptions.AccessDenied(message=_('你不是此工单的指派处理人。')))
            else:
                return view.exception_response(exceptions.AccessDenied(message=_('你没有联邦管理员权限')))
        elif ticket.submitter_id != request.user.id:
            return view.exception_response(exceptions.AccessDenied(message=_('你没有此工单的访问权限')))

        if ticket.status == Ticket.Status.CLOSED.value:
            return view.exception_response(
                exceptions.ConflictTicketStatus(message=_('”已关闭“状态的工单不允许提交回复。')))

        try:
            folowup = TicketManager.create_followup_reply(
                ticket_id=ticket.id, user=user, comment=comment
            )
        except Exception as exc:
            return view.exception_response(exceptions.Error(message=_('添加工单回复错误。') + str(exc)))

        try:
            if user.id == ticket.submitter_id:
                receivers = [ticket.assigned_to.username] if ticket.assigned_to else []
            else:
                receivers = [ticket.username]

            if receivers:
                TicketEmailNotifier.new_followup_notice(receivers=receivers, ticket=ticket, folowup=folowup)
        except Exception as exc:
            pass

        return Response(data=ticket_serializers.FollowUpSerializer(instance=folowup).data)

    @staticmethod
    def _add_followup_validate_params(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'comment' in s_errors:
                exc = exceptions.BadRequest(message=_('无效的回复。') + s_errors['comment'][0], code='InvalidComment')
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = exceptions.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data
        comment = data['comment']

        if not comment:
            raise exceptions.BadRequest(message=_('回复内容不能为空。'), code='InvalidComment')

        return data

    @staticmethod
    def list_followup(view: AsRoleGenericViewSet, request, kwargs):
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
                return view.exception_response(exceptions.AccessDenied(message=_('你没有联邦管理员权限')))
        elif ticket.submitter_id != request.user.id:
            return view.exception_response(exceptions.AccessDenied(message=_('你没有此工单的访问权限')))

        queryset = TicketManager.get_ticket_followup_queryset(ticket_id=ticket.id, is_only_replay=not has_role)
        paginator = FollowUpMarkerCursorPagination()
        try:
            followups = paginator.paginate_queryset(queryset=queryset, request=request, view=view)
            serializer = ticket_serializers.FollowUpSerializer(followups, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def take_ticket(view: AsRoleGenericViewSet, request, kwargs):
        """
        领取一个待处理的工单
        """
        ticket_id = kwargs[view.lookup_field]

        if not request.user.is_federal_admin():
            return view.exception_response(exceptions.AccessDenied(message=_('你没有联邦管理员权限')))

        try:
            ticket = TicketManager.get_ticket(ticket_id=ticket_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if ticket.assigned_to_id:
            return view.exception_response(
                exceptions.AccessDenied(message=_('工单已指派了处理人。')))

        if ticket.status not in [Ticket.Status.OPEN.value, Ticket.Status.PROGRESS.value]:
            return view.exception_response(
                exceptions.ConflictTicketStatus(message=_('只能领取“打开”和“处理中”的工单')))

        try:
            TicketManager.ticket_assigned_to_user(user=request.user, ticket=ticket, assigned_to=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={})

    @staticmethod
    def ticket_assigned_to(view: AsRoleGenericViewSet, request, kwargs):
        ticket_id = kwargs[view.lookup_field]
        username = kwargs.get('username', '')

        try:
            ticket = TicketManager.get_ticket(ticket_id=ticket_id)
            if ticket.status == Ticket.Status.CLOSED.value:
                return view.exception_response(exceptions.ConflictTicketStatus(message=_('工单已关闭。')))

            if not request.user.is_federal_admin():
                return view.exception_response(
                    exceptions.AccessDenied(message=_('你没有此工单的分配权限。')))

            # UserNotExist
            assigned_to_user = get_user_by_name(username=username)
            if not assigned_to_user.is_federal_admin():
                return view.exception_response(
                    exceptions.ConflictError(message=_('工单只允许转交给联邦管理员。')))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if ticket.assigned_to_id == assigned_to_user.id:
            return Response(data={})

        try:
            TicketManager.ticket_assigned_to_user(
                user=request.user, ticket=ticket, assigned_to=assigned_to_user
            )
        except Exception as exc:
            return view.exception_response(exceptions.Error(message=_('更改工单处理人失败。') + str(exc)))

        return Response(data={})

    @staticmethod
    def add_ticket_rating(view: AsRoleGenericViewSet, request, kwargs):
        """
        提交工单评价
        """
        ticket_id = kwargs[view.lookup_field]
        user = request.user

        try:
            serializer = view.get_serializer(data=request.data)
            if not serializer.is_valid(raise_exception=False):
                s_errors = serializer.errors
                if 'comment' in s_errors:
                    exc = exceptions.BadRequest(message=_('无效的评论。') + s_errors['comment'][0], code='InvalidComment')
                elif 'score' in s_errors:
                    exc = exceptions.BadRequest(
                        message=_('无效评分，评分只允许1-5。') + s_errors['score'][0], code='InvalidScore')
                else:
                    msg = serializer_error_msg(serializer.errors)
                    exc = exceptions.BadRequest(message=msg)

                raise exc
        except exceptions.Error as exc:
            return view.exception_response(exc)

        data = serializer.validated_data
        comment = data['comment']
        score = data['score']

        try:
            ticket = TicketManager.get_ticket(ticket_id=ticket_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if ticket.submitter_id != user.id:
            return view.exception_response(exceptions.AccessDenied(message=_('你没有此工单的访问权限')))

        if ticket.status != Ticket.Status.CLOSED.value:
            return view.exception_response(
                exceptions.ConflictTicketStatus(message=_('只允许评价”已关闭“状态的工单。')))

        rat = TicketRating.objects.filter(ticket_id=ticket.id).first()
        if rat is not None:
            return view.exception_response(
                exceptions.TargetAlreadyExists(message=_('工单已评价。')))

        try:
            rating = TicketManager.create_ticket_rating(
                ticket=ticket, score=score, comment=comment, user=user
            )
        except Exception as exc:
            return view.exception_response(exceptions.Error(message=_('添加工单评价错误。') + str(exc)))

        return Response(data=ticket_serializers.TicketRatingSerializer(instance=rating).data)

    @staticmethod
    def query_ticket_rating(view: AsRoleGenericViewSet, request, kwargs):
        """
        提交工单评价

            * 登录用户都有权限查询
        """
        ticket_id = kwargs[view.lookup_field]
        rating = TicketRating.objects.filter(ticket_id=ticket_id).first()

        ratings = []
        if rating is not None:
            rat = ticket_serializers.TicketRatingSerializer(instance=rating).data
            ratings.append(rat)

        return Response(data={'ratings': ratings})
