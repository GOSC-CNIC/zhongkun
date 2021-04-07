from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.response import Response

from servers.models import Server
from service.managers import UserQuotaManager
from applyment.models import ApplyQuota
from applyment.managers import ApplyQuotaManager
from . import serializers
from . import exceptions


def serializer_error_msg(errors, default=''):
    """
    获取一个错误信息

    :param errors: serializer.errors
    :param default:
    :return:
        str
    """
    msg = default
    try:
        if isinstance(errors, list):
            for err in errors:
                msg = str(err)
                break
        elif isinstance(errors, dict):
            for key in errors:
                val = errors[key]
                msg = f'{key}, {str(val[0])}'
                break
    except Exception:
        pass

    return msg


class UserQuotaHandler:
    @staticmethod
    def list_quotas(view, request, kwargs):
        service_id = request.query_params.get('service', None)
        usable = request.query_params.get('usable', '').lower()
        usable = True if usable == 'true' else False

        try:
            queryset = UserQuotaManager().filter_quota_queryset(user=request.user, service=service_id, usable=usable)
            paginator = view.paginator
            quotas = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.UserQuotaSerializer(quotas, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

        return response

    @staticmethod
    def list_quota_servers(view, request, kwargs):
        quota_id = kwargs.get(view.lookup_field)
        quota = UserQuotaManager().get_quota_by_id(quota_id)
        if not quota:
            return view.exception_reponse(
                exceptions.NotFound(message='资源配额不存在'))

        if quota.user_id != request.user.id:
            return view.exception_reponse(
                exceptions.AccessDenied(message=_('无权访问此资源配额')))

        try:
            queryset = Server.objects.filter(user_quota=quota)
            paginator = view.pagination_class()
            servers = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ServerSimpleSerializer(servers, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)


class ApplyUserQuotaHandler:
    @staticmethod
    def list_apply(view, request, kwargs):
        """
        list资源配额申请
        """
        try:
            queryset = ApplyQuotaManager().get_user_apply_queryset(user=request.user)
            paginator = view.pagination_class()
            applys = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = view.get_serializer(instance=applys, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

    @staticmethod
    def create_apply(view, request, kwargs):
        """
        提交一个资源配额申请
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_reponse(exceptions.BadRequest(msg))

        count = ApplyQuota.objects.filter(user=request.user,
                                          status=ApplyQuota.STATUS_WAIT).count()
        if count >= 6:
            return view.exception_reponse(exceptions.TooManyQuotaApply())

        data = serializer.validated_data
        service_id = data.get('service_id', None)
        try:
            service = view.get_service_by_id(service_id)
        except exceptions.Error as exc:
            return view.exception_reponse(exc)

        apply = ApplyQuota()
        apply.private_ip = data.get('private_ip', 0)
        apply.public_ip = data.get('public_ip', 0)
        apply.vcpu = data.get('vcpu', 0)
        apply.ram = data.get('ram', 0) * 1024
        apply.disk_size = data.get('disk_size', 0)
        apply.duration_days = data.get('duration_days', 1)
        apply.company = data.get('company', '')
        apply.contact = data.get('contact', '')
        apply.purpose = data.get('purpose', '')
        apply.service = service
        apply.user = request.user
        apply.save()
        r_data = serializers.ApplyQuotaSerializer(instance=apply).data
        return Response(data=r_data, status=201)

    @staticmethod
    def pending_apply(view, request, kwargs):
        """
        配额申请审批挂起中,只允许“待审批（wait）”状态的资源配额申请被服务管理者挂起
        """
        pk = kwargs.get(view.lookup_field)
        apply = ApplyQuota.objects.select_related('service').filter(id=pk).first()
        if not apply:
            return view.exception_reponse(exceptions.NotFound(
                message=_('资源配额申请不存在')))

        if not apply.service.user_has_perm(request.user):
            return view.exception_reponse(exceptions.AccessDenied(
                message=_('没有审批操作资源配额申请的权限')
            ))

        if not apply.is_wait_status():
            return view.exception_reponse(exceptions.ConflictError(
                message=_('只允许“待审批”状态的资源配额申请被挂起')
            ))

        try:
            if not apply.set_pending(user=request.user):
                raise Exception('挂起申请失败')
        except Exception as exc:
            return view.exception_reponse(exc)

        try:
            r_data = serializers.ApplyQuotaSerializer(instance=apply).data
        except Exception as e:
            r_data = None

        return Response(data=r_data, status=200)

    @staticmethod
    def cancel_apply(view, request, kwargs):
        """
        取消配额申请，只允许申请者取消待审批（wait）状态的申请
        """
        pk = kwargs.get(view.lookup_field)
        apply = ApplyQuota.objects.filter(id=pk).first()
        if not apply:
            return view.exception_reponse(exceptions.NotFound(
                message=_('资源配额申请不存在')))

        if not apply.user_id or apply.user_id != request.user.id:
            return view.exception_reponse(exceptions.AccessDenied(
                message=_('你没有权限取消资源配额申请')))

        if apply.is_cancel_status:
            try:
                r_data = serializers.ApplyQuotaSerializer(instance=apply).data
            except Exception as e:
                r_data = None

            return Response(data=r_data, status=200)

        if not apply.is_wait_status():
            return view.exception_reponse(exceptions.ConflictError(
                message=_('只允许“待审批”状态的资源配额申请被取消')
            ))

        try:
            if not apply.set_cancel():
                raise Exception('取消申请失败')
        except Exception as exc:
            return view.exception_reponse(exc)

        try:
            r_data = serializers.ApplyQuotaSerializer(instance=apply).data
        except Exception as e:
            r_data = None

        return Response(data=r_data, status=200)

    @staticmethod
    def modify_apply(view, request, kwargs):
        """
        修改资源配额申请, 只允许申请者修改待审批（wait）状态的申请
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_reponse(exceptions.BadRequest(msg))

        pk = kwargs.get(view.lookup_field)
        apply = ApplyQuota.objects.filter(id=pk).first()
        if not apply:
            return view.exception_reponse(exceptions.NotFound(
                message=_('资源配额申请不存在')))

        # 用户只能修改自己的申请
        if not apply.user_id or apply.user_id != request.user.id:
            return view.exception_reponse(exceptions.AccessDenied(
                message=_('你没有权限修改资源配额申请')))

        if not apply.is_wait_status():
            return view.exception_reponse(exceptions.ConflictError(
                message=_('只允许“待审批”状态的资源配额申请被修改')
            ))

        update_fields = []
        data = serializer.validated_data
        service_id = data.get('service_id', None)
        if service_id:
            try:
                service = view.get_service_by_id(service_id)
            except exceptions.Error as exc:
                return view.exception_reponse(exc)

            apply.service = service
            update_fields.append('service')

        private_ip = data.get('private_ip', None)
        if private_ip is not None:
            apply.private_ip = private_ip
            update_fields.append('private_ip')

        public_ip = data.get('public_ip', None)
        if public_ip is not None:
            apply.public_ip = public_ip
            update_fields.append('public_ip')

        vcpu = data.get('vcpu', None)
        if vcpu is not None:
            apply.vcpu = vcpu
            update_fields.append('vcpu')

        ram = data.get('ram', None)
        if ram is not None:
            apply.ram = ram * 1024
            update_fields.append('ram')

        disk_size = data.get('disk_size', None)
        if disk_size is not None:
            apply.disk_size = disk_size
            update_fields.append('disk_size')

        duration_days = data.get('duration_days', None)
        if duration_days is not None:
            apply.duration_days = duration_days
            update_fields.append('duration_days')

        company = data.get('company', '')
        if company is not None:
            apply.company = company
            update_fields.append('company')

        contact = data.get('contact', '')
        if contact is not None:
            apply.contact = contact
            update_fields.append('contact')

        purpose = data.get('purpose', '')
        if purpose is not None:
            apply.purpose = purpose
            update_fields.append('purpose')

        apply.save(update_fields=update_fields)
        try:
            r_data = serializers.ApplyQuotaSerializer(instance=apply).data
        except Exception as e:
            r_data = None

        return Response(data=r_data, status=200)

    @staticmethod
    def approve_apply(view, request, kwargs, approve: str = 'pass'):
        """
        审批配额申请，只允许服务管理者审批处于“审批中”状态的资源配额申请

        :param view:
        :param request:
        :param kwargs:
        :param approve: 'pass' or 'reject'
        """
        pk = kwargs.get(view.lookup_field)
        apply = ApplyQuota.objects.select_related('service').filter(id=pk).first()
        if not apply:
            return view.exception_reponse(exceptions.NotFound(
                message=_('资源配额申请不存在')))

        if not apply.service.user_has_perm(request.user):
            return view.exception_reponse(exceptions.AccessDenied(
                message=_('没有审批操作资源配额申请的权限')
            ))

        if not apply.is_pending_status():
            return view.exception_reponse(exceptions.ConflictError(
                message=_('只允许审批处于“审批中”状态的资源配额申请')
            ))

        try:
            if approve == 'reject':
                if not apply.set_reject(user=request.user):
                    raise Exception('拒绝申请失败')
            elif approve == 'pass':
                apply.do_pass(user=request.user)
            else:
                raise Exception('无效的参数')
        except Exception as exc:
            return view.exception_reponse(exc)

        try:
            r_data = serializers.ApplyQuotaSerializer(instance=apply).data
        except Exception as e:
            r_data = None

        return Response(data=r_data, status=200)

    @staticmethod
    def reject_apply(view, request, kwargs):
        """
        拒绝配额申请
        """
        return ApplyUserQuotaHandler.approve_apply(view=view, request=request,
                                                   kwargs=kwargs, approve='reject')

    @staticmethod
    def pass_apply(view, request, kwargs):
        """
        通过配额申请
        """
        return ApplyUserQuotaHandler.approve_apply(view=view, request=request,
                                                   kwargs=kwargs, approve='pass')


