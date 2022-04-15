from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.utils.http import urlquote
from django.http import FileResponse
from django.urls import reverse
from rest_framework.response import Response

from servers.models import Server
from service.managers import (
    UserQuotaManager, VmServiceApplyManager, OrganizationApplyManager,
    ServicePrivateQuotaManager, ServiceShareQuotaManager, ServiceManager,
    ApplyQuotaManager
)
from service.models import ApplyQuota
from vo.managers import VoManager, VoMemberManager
from activity.managers import QuotaActivityManager
from utils import storagers
from utils import time
from core import errors as exceptions
from api import serializers


User = get_user_model()


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
                if isinstance(val, list):
                    msg = f'{key}, {str(val[0])}'
                else:
                    msg = f'{key}, {str(val)}'

                break
    except Exception:
        pass

    return msg


class UserQuotaHandler:
    @staticmethod
    def list_quotas(view, request, kwargs):
        """
        list用户个人的资源配额
        """
        service_id = request.query_params.get('service', None)
        usable = request.query_params.get('usable', '').lower()
        usable = True if usable == 'true' else False
        deleted_query = request.query_params.get('deleted', None)
        if deleted_query is None:
            deleted = None
        elif deleted_query.lower() == 'false':
            deleted = False
        else:
            deleted = True

        try:
            queryset = UserQuotaManager().filter_user_quota_queryset(
                user=request.user, service=service_id, usable=usable, deleted=deleted)
            paginator = view.paginator
            quotas = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.UserQuotaSerializer(quotas, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            err = exceptions.convert_to_error(exc)
            return Response(err.err_data(), status=err.status_code)

        return response

    @staticmethod
    def list_vo_quotas(view, request, kwargs):
        """
        list vo组的资源配额
        """
        service_id = request.query_params.get('service', None)
        usable = request.query_params.get('usable', '').lower()
        usable = True if usable == 'true' else False
        vo_id = kwargs.get('vo_id')

        try:
            vo, member = VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
            queryset = UserQuotaManager().filter_vo_quota_queryset(
                vo=vo, service=service_id, usable=usable)
            paginator = view.paginator
            quotas = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.UserQuotaSerializer(quotas, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            err = exceptions.convert_to_error(exc)
            return Response(err.err_data(), status=err.status_code)

    @staticmethod
    def list_quota_servers(view, request, kwargs):
        """
        需要配额属于用户，或者属于用户所在的vo组
        """
        quota_id = kwargs.get(view.lookup_field)
        try:
            quota = UserQuotaManager().get_user_read_perm_quota(quota_id, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            queryset = Server.objects.filter(user_quota=quota)
            paginator = view.pagination_class()
            servers = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ServerSimpleSerializer(servers, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            err = exceptions.convert_to_error(exc)
            return Response(err.err_data(), status=err.status_code)

    @staticmethod
    def delete_quota(view, request, kwargs):
        quota_id = kwargs.get(view.lookup_field)
        try:
            UserQuotaManager().delete_quota_soft(quota_id, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def detail_quota(view, request, kwargs):
        quota_id = kwargs.get(view.lookup_field)

        try:
            if view.is_as_admin_request(request):
                quota = UserQuotaManager().get_admin_read_perm_quota(quota_id, user=request.user)
            else:
                quota = UserQuotaManager().get_user_read_perm_quota(quota_id, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        data = serializers.UserQuotaDetailSerializer(instance=quota).data
        return Response(data=data)


class ApplyUserQuotaHandler:
    @staticmethod
    def get_list_queryset(request, is_admin: bool = False):
        """
        获取查询集

        :param request:
        :param is_admin: True: 有管理权限的申请记录查询集；False: 用户自己的申请记录查询集；
        """
        deleted = request.query_params.get('deleted', None)
        service_id = request.query_params.get('service', None)
        status = request.query_params.getlist('status', None)
        if not status or status == ['']:
            status = None

        if deleted:
            if deleted == 'true':
                deleted = True
            elif deleted == 'false':
                deleted = False
            else:
                deleted = None

        if is_admin:
            return ApplyQuotaManager().admin_filter_apply_queryset(
                user=request.user, service_id=service_id, deleted=deleted, status=status)
        else:
            return ApplyQuotaManager().filter_user_apply_queryset(
                user=request.user, service_id=service_id, deleted=deleted, status=status)

    @staticmethod
    def list_apply(view, request, kwargs):
        """
        list user资源配额申请
        """
        try:
            queryset = ApplyUserQuotaHandler.get_list_queryset(request=request)
            paginator = view.pagination_class()
            applys = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = view.get_serializer(instance=applys, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            err = exceptions.convert_to_error(exc)
            return Response(err.err_data(), status=err.status_code)

    @staticmethod
    def admin_list_apply(view, request, kwargs):
        """
        管理员list资源配额申请
        """
        try:
            queryset = ApplyUserQuotaHandler.get_list_queryset(request=request, is_admin=True)
            paginator = view.pagination_class()
            applys = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = view.get_serializer(instance=applys, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            err = exceptions.convert_to_error(exc)
            return Response(err.err_data(), status=err.status_code)

    @staticmethod
    def vo_leader_list(view, request, kwargs):
        """
        vo组管理员列举vo组的资源配额申请
        """
        vo_id = kwargs.get('vo_id')
        deleted = request.query_params.get('deleted', None)
        service_id = request.query_params.get('service', None)
        status = request.query_params.getlist('status', None)
        if not status or status == ['']:
            status = None

        if deleted:
            if deleted == 'true':
                deleted = True
            elif deleted == 'false':
                deleted = False
            else:
                deleted = None

        try:
            vo, member = VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=request.user)
            queryset = ApplyQuotaManager().filter_vo_apply_queryset(
                vo=vo, service_id=service_id, deleted=deleted, status=status)

            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = view.get_serializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            err = exceptions.convert_to_error(exc)
            return Response(err.err_data(), status=err.status_code)

    @staticmethod
    def admin_detail_apply(view, request, kwargs):
        """
        管理员查询资源配额申请详细信息
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = ApplyQuotaManager().get_has_manage_perm_apply(pk=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=serializers.ApplyQuotaDetailWithVoSerializer(apply).data)

    @staticmethod
    def user_or_vo_apply_detail(view, request, kwargs):
        """
        查询用户个人或vo组资源配额申请详细信息
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = ApplyQuotaManager().get_user_or_vo_apply(pk=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=serializers.ApplyQuotaDetailWithVoSerializer(apply).data)

    @staticmethod
    def create_user_apply_handle(apply: ApplyQuota, user) -> ApplyQuota:
        """
        个人配额申请
        """
        count = ApplyQuota.objects.filter(user=user, deleted=False,
                                          classification=ApplyQuota.Classification.PERSONAL,
                                          status=ApplyQuota.STATUS_WAIT).count()
        if count >= 6:
            raise exceptions.TooManyApply()

        apply.classification = apply.Classification.PERSONAL
        apply.vo_id = None

        return apply

    @staticmethod
    def create_vo_apply_handle(apply: ApplyQuota, vo_id: str, user) -> ApplyQuota:
        """
        vo组配额申请

        :raises: Error
        """
        vo, member = VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=user)
        count = ApplyQuota.objects.filter(vo=vo, deleted=False,
                                          classification=ApplyQuota.Classification.VO,
                                          status=ApplyQuota.STATUS_WAIT).count()
        if count >= 6:
            raise exceptions.TooManyApply(_('vo组已提交了多个申请，待审批，暂不能提交更多的申请'))

        apply.classification = apply.Classification.VO
        apply.vo = vo

        return apply

    @staticmethod
    def create_apply(view, request, kwargs):
        """
        提交一个资源配额申请
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        service_id = data.get('service_id', None)
        try:
            service = view.get_service_by_id(service_id)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        apply = ApplyQuota()
        apply.private_ip = data.get('private_ip', 0)
        apply.public_ip = data.get('public_ip', 0)
        apply.vcpu = data.get('vcpu', 0)
        apply.ram = data.get('ram', 0)
        apply.disk_size = data.get('disk_size', 0)
        apply.duration_days = data.get('duration_days', 1)
        apply.company = data.get('company', '')
        apply.contact = data.get('contact', '')
        apply.purpose = data.get('purpose', '')
        apply.service = service
        apply.user = request.user

        vo_id = data.get('vo_id', None)
        try:
            if vo_id:
                apply = ApplyUserQuotaHandler.create_vo_apply_handle(apply=apply, vo_id=vo_id, user=request.user)
            else:
                apply = ApplyUserQuotaHandler.create_user_apply_handle(apply=apply, user=request.user)

            apply.save()
        except Exception as exc:
            return view.exception_response(exc)

        r_data = serializers.ApplyQuotaDetailWithVoSerializer(instance=apply).data
        return Response(data=r_data, status=201)

    @staticmethod
    def pending_apply(view, request, kwargs):
        """
        配额申请审批挂起中,只允许“待审批（wait）”状态的资源配额申请被服务管理者挂起
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = ApplyQuotaManager().get_has_manage_perm_apply(pk=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        if not apply.is_wait_status():
            return view.exception_response(exceptions.ConflictError(
                message=_('只允许“待审批”状态的资源配额申请被挂起')
            ))

        try:
            if not apply.set_pending(user=request.user):
                raise Exception('挂起申请失败')
        except Exception as exc:
            return view.exception_response(exc)

        try:
            r_data = serializers.ApplyQuotaSerializer(instance=apply).data
        except Exception as e:
            r_data = None

        return Response(data=r_data, status=200)

    @staticmethod
    def cancel_apply(view, request, kwargs):
        """
        取消配额申请，只允许申请者取消待审批（wait）状态的申请
        或者vo组管理员取消待审批（wait）状态的vo组配额申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = ApplyQuotaManager().get_user_or_vo_apply(pk=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        if apply.is_cancel_status():
            try:
                r_data = serializers.ApplyQuotaSerializer(instance=apply).data
            except Exception as e:
                r_data = None

            return Response(data=r_data, status=200)

        if not apply.is_wait_status():
            return view.exception_response(exceptions.ConflictError(
                message=_('只允许“待审批”状态的资源配额申请被取消')
            ))

        try:
            if not apply.set_cancel():
                raise Exception('取消申请失败')
        except Exception as exc:
            return view.exception_response(exc)

        try:
            r_data = serializers.ApplyQuotaSerializer(instance=apply).data
        except Exception as e:
            r_data = None

        return Response(data=r_data, status=200)

    @staticmethod
    def modify_apply(view, request, kwargs):
        """
        修改资源配额申请, 只允许申请者修改待审批（wait）和拒绝（reject）状态的个人的申请，
        或者vo组管理员修改待审批（wait）和拒绝（reject）状态的vo组配额申请
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        pk = kwargs.get(view.lookup_field)
        try:
            apply = ApplyQuotaManager().get_user_or_vo_apply(pk=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        if not (apply.is_wait_status() or apply.is_reject_status()):
            return view.exception_response(exceptions.ConflictError(
                message=_('只允许“待审批”和“拒绝”状态的资源配额申请被修改')
            ))

        update_fields = []
        data = serializer.validated_data
        service_id = data.get('service_id', None)
        if service_id:
            try:
                service = view.get_service_by_id(service_id)
            except exceptions.Error as exc:
                return view.exception_response(exc)

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
            apply.ram = ram
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

        # 修改后回到待审批状态
        apply.status = apply.STATUS_WAIT
        apply.result_desc = ''
        update_fields.append('status')
        update_fields.append('result_desc')
        try:
            apply.save(update_fields=update_fields)
        except Exception as exc:
            return view.exception_response(exc)

        try:
            r_data = serializers.ApplyQuotaSerializer(instance=apply).data
        except Exception as e:
            r_data = None

        return Response(data=r_data, status=200)

    @staticmethod
    def approve_apply(view, request, kwargs, approve: str, reason: str):
        """
        审批配额申请，只允许服务管理者审批处于“审批中”状态的资源配额申请

        :param view:
        :param request:
        :param kwargs:
        :param approve: 'pass' or 'reject'
        :param reason: 审批结果说明，拒绝理由
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = ApplyQuotaManager().get_has_manage_perm_apply(pk=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        if not apply.is_pending_status():
            return view.exception_response(exceptions.ConflictError(
                message=_('只允许审批处于“审批中”状态的资源配额申请')
            ))

        try:
            if approve == 'reject':
                if not apply.set_reject(user=request.user, reason=reason):
                    raise Exception('拒绝申请失败')
            elif approve == 'pass':
                apply.do_pass(user=request.user)
            else:
                raise Exception('无效的参数')
        except Exception as exc:
            return view.exception_response(exc)

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
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        reason = serializer.validated_data.get('reason')
        return ApplyUserQuotaHandler.approve_apply(view=view, request=request,
                                                   kwargs=kwargs, approve='reject', reason=reason)

    @staticmethod
    def pass_apply(view, request, kwargs):
        """
        通过配额申请
        """
        return ApplyUserQuotaHandler.approve_apply(view=view, request=request,
                                                   kwargs=kwargs, approve='pass', reason='pass')

    @staticmethod
    def delete_apply(view, request, kwargs):
        """
        删除配额申请，只允许申请者删除个人配额申请，或者vo组管理员删除vo组配额申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = ApplyQuotaManager().get_user_or_vo_apply(pk=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        try:
            apply.do_soft_delete()
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)


class ApplyOrganizationHandler:
    @staticmethod
    def get_list_queryset(request, is_admin: bool = False):
        """
        获取查询集

        :param request:
        :param is_admin: True: 有管理权限的申请记录查询集；False: 用户自己的申请记录查询集；
        """
        deleted = request.query_params.get('deleted', None)
        status = request.query_params.getlist('status', None)
        if not status or status == ['']:
            status = None
        if isinstance(status, list):
            if not set(status).issubset(set(OrganizationApplyManager.model.Status.values)):
                raise exceptions.InvalidArgument(message=_('参数"status"包含无效的值'))

        if deleted:
            deleted = deleted.lower()
            if deleted == 'true':
                deleted = True
            elif deleted == 'false':
                deleted = False
            else:
                deleted = None

        if is_admin:
            return OrganizationApplyManager().admin_filter_apply_queryset(
                deleted=deleted, status=status)
        else:
            return OrganizationApplyManager().filter_user_apply_queryset(
                user=request.user, deleted=deleted, status=status)

    @staticmethod
    def list_apply(view, request, kwargs):
        """
        list user机构加入申请
        """
        try:
            queryset = ApplyOrganizationHandler.get_list_queryset(request=request)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyOrganizationSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def admin_list_apply(view, request, kwargs):
        """
        管理员list机构加入申请
        """
        if not request.user.is_federal_admin():
            return view.exception_response(
                exc=exceptions.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限')))
        try:
            queryset = ApplyOrganizationHandler.get_list_queryset(request=request, is_admin=True)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyOrganizationSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create_apply(view, request, kwargs):
        """
        提交一个机构/数据中心创建申请
        """
        oa_mgr = OrganizationApplyManager()
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        count = oa_mgr.get_in_progress_apply_count(user=request.user)
        if count >= 6:
            return view.exception_response(exceptions.TooManyApply())

        try:
            apply = oa_mgr.create_apply(data=serializer.validated_data, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.ApplyOrganizationSerializer(instance=apply).data
        return Response(data=rdata)

    @staticmethod
    def apply_action(view, request, kwargs):
        """
            cancel：取消申请
            pending：挂起申请（审核中）
            reject：拒绝
            pass：通过
            delete: 删除
        """
        _action = kwargs.get('action', '').lower()
        if _action == 'pending':
            return ApplyOrganizationHandler.pending_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'cancel':
            return ApplyOrganizationHandler.cancel_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'reject':
            return ApplyOrganizationHandler.reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pass':
            return ApplyOrganizationHandler.pass_apply(view=view, request=request, kwargs=kwargs)

        return view.exception_response(
            exc=exceptions.BadRequest(message=_('不支持操作命令"{action}"').format(action=_action)))


    @staticmethod
    def pending_apply(view, request, kwargs):
        """
        挂起一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().pending_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def cancel_apply(view, request, kwargs):
        """
        取消一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().cancel_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pass_apply(view, request, kwargs):
        """
        审核通过一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def reject_apply(view, request, kwargs):
        """
        审核拒绝一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def delete_apply(view, request, kwargs):
        """
        软删除一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            OrganizationApplyManager().delete_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)


class ApplyVmServiceHandler:
    @staticmethod
    def get_list_queryset(request, is_admin: bool = False):
        """
        获取查询集

        :param request:
        :param is_admin: True: 有管理权限的申请记录查询集；False: 用户自己的申请记录查询集；

        :raises: Error
        """
        organization_id = request.query_params.get('organization', None)
        deleted = request.query_params.get('deleted', None)
        if deleted:
            deleted = deleted.lower()
            if deleted == 'true':
                deleted = True
            elif deleted == 'false':
                deleted = False
            else:
                deleted = None

        status = request.query_params.getlist('status', None)
        if not status or status == ['']:
            status = None
        if isinstance(status, list):
            if not set(status).issubset(set(VmServiceApplyManager.model.Status.values)):
                raise exceptions.InvalidArgument(message=_('参数"status"包含无效的值'))

        if is_admin:
            return VmServiceApplyManager().admin_filter_apply_queryset(
                deleted=deleted, organization_id=organization_id, status=status)
        else:
            return VmServiceApplyManager().filter_user_apply_queryset(
                user=request.user, deleted=deleted, organization_id=organization_id, status=status)

    @staticmethod
    def list_apply(view, request, kwargs):
        """
        list user云主机服务接入申请
        """
        try:
            queryset = ApplyVmServiceHandler.get_list_queryset(request=request)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyVmServiceSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def admin_list_apply(view, request, kwargs):
        """
        管理员list云主机服务接入申请
        """
        if not request.user.is_federal_admin():
            return view.exception_response(
                exc=exceptions.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限')))
        try:
            queryset = ApplyVmServiceHandler.get_list_queryset(request=request, is_admin=True)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyVmServiceSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create_apply(view, request, kwargs):
        """
        提交一个服务接入申请
        """
        vsa_mgr = VmServiceApplyManager()
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        count = vsa_mgr.get_in_progress_apply_count(user=request.user)
        if count >= 6:
            return view.exception_response(exceptions.TooManyApply())

        try:
            apply = vsa_mgr.create_apply(data=serializer.validated_data, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.ApplyVmServiceSerializer(instance=apply).data
        return Response(data=rdata)

    @staticmethod
    def apply_action(view, request, kwargs):
        """
            cancel：取消申请
            pending：挂起申请（审核中）
            first_pass：初审通过
            first_reject：初审拒绝
            test：测试
            reject：拒绝
            pass：通过
        """
        _action = kwargs.get('action', '').lower()
        if _action == 'cancel':
            return ApplyVmServiceHandler.cancel_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pending':
            return ApplyVmServiceHandler.pending_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'first_reject':
            return ApplyVmServiceHandler.first_reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'first_pass':
            return ApplyVmServiceHandler.first_pass_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'test':
            return ApplyVmServiceHandler.test_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'reject':
            return ApplyVmServiceHandler.reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pass':
            return ApplyVmServiceHandler.pass_apply(view=view, request=request, kwargs=kwargs)

        return view.exception_response(
            exc=exceptions.BadRequest(message=_('不支持操作命令"{action}"').format(action=_action)))

    @staticmethod
    def cancel_apply(view, request, kwargs):
        """
        取消一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().cancel_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pending_apply(view, request, kwargs):
        """
        挂起一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().pending_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def first_reject_apply(view, request, kwargs):
        """
        初审拒绝一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().first_reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def first_pass_apply(view, request, kwargs):
        """
        初审通过一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().first_pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def test_apply(view, request, kwargs):
        """
        测试一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply, test_msg = VmServiceApplyManager().test_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data={
            'ok': False if test_msg else True,
            'message': test_msg,
            'apply': serializer.data
        })

    @staticmethod
    def reject_apply(view, request, kwargs):
        """
        拒绝一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pass_apply(view, request, kwargs):
        """
        通过一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def delete_apply(view, request, kwargs):
        """
        软删除一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            VmServiceApplyManager().delete_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)


class MediaHandler:
    @staticmethod
    def media_upload(view, request, kwargs):
        paths = kwargs.get(view.lookup_field, '').rsplit('/', maxsplit=1)
        if len(paths) == 2:
            storage_to, filename = paths
        else:
            storage_to, filename = '', paths[-1]

        request.upload_handlers = [
            storagers.Md5TemporaryFileUploadHandler(request=request),
            storagers.Md5MemoryFileUploadHandler(request=request)
        ]

        content_md5 = view.request.headers.get('Content-MD5', '')
        if not content_md5:
            return view.exception_response(exc=exceptions.InvalidDigest())

        content_length = request.headers.get('content-length')
        if not content_length:
            return view.exception_response(
                exc=exceptions.BadRequest(
                    message='header "Content-Length" is required'))

        try:
            content_length = int(content_length)
        except (ValueError, TypeError):
            raise exceptions.BadRequest(
                message='header "Content-Length" is invalid')

        try:
            request.parser_context['kwargs']['filename'] = filename
            put_data = request.data
        except Exception as exc:
            return view.exception_response(exceptions.Error.from_error(exc))

        file = put_data.get('file')
        if not file:
            return view.exception_response(
                exc=exceptions.BadRequest(message='Request body is empty.'))

        if content_length != file.size:
            return view.exception_response(
                exc=exceptions.BadRequest(
                    message='The length of body not same header "Content-Length"'))

        if content_md5 != file.file_md5:
            return view.exception_response(
                exc=exceptions.BadDigest())

        return MediaHandler._storage_media(view=view, subpath=storage_to,
                                           filename=filename, file=file)

    @staticmethod
    def _storage_media(view, subpath: str, filename: str, file):
        if storagers.LogoFileStorager.is_start_prefix(sub_path=subpath):
            filename = storagers.LogoFileStorager.storage_filename(filename=filename, md5=file.file_md5)
            storager = storagers.LogoFileStorager(filename=filename)
        elif storagers.CertificationFileStorager.is_start_prefix(sub_path=subpath):
            filename = storagers.CertificationFileStorager.storage_filename(filename=filename, md5=file.file_md5)
            storager = storagers.CertificationFileStorager(filename=filename)
        else:
            storager = storagers.MediaFileStorager(filename=filename, storage_to=subpath)

        try:
            storager.save_file(file)
        except Exception as exc:
            storager.delete()
            return view.exception_response(exc)

        api_path = reverse('api:media-detail', kwargs={'url_path': storager.relative_path()})
        return Response(data={'url_path': api_path})

    @staticmethod
    def media_download(view, request, kwargs):
        path = kwargs.get(view.lookup_field, '')
        paths = path.rsplit('/', maxsplit=1)
        if len(paths) == 2:
            storage_to, filename = paths
        else:
            storage_to, filename = '', paths[-1]

        if not bool(request.user and request.user.is_authenticated):
            if not (storage_to == 'logo' or storage_to.startswith('logo/')):
                return view.exception_response(exceptions.AccessDenied(message='未认证'))

        return MediaHandler.media_download_response(
            view=view, subpath=storage_to, filename=filename)

    @staticmethod
    def media_download_response(view, subpath: str, filename: str):
        storager = storagers.MediaFileStorager(
            filename=filename, storage_to=subpath)

        if not storager.is_exists():
            return view.exception_response(exc=exceptions.NotFound())

        filesize = storager.size()
        file_generator = storager.get_file_generator()
        last_modified = time.time_to_gmt(storager.last_modified_time())

        filename = urlquote(filename)  # 中文文件名需要
        response = FileResponse(file_generator)
        response['Content-Length'] = filesize
        response['Content-Type'] = 'application/octet-stream'  # 注意格式
        response['Content-Disposition'] = f"attachment;filename*=utf-8''{filename}"  # 注意filename 这个是下载后的名字
        response['Cache-Control'] = 'max-age=20'

        if last_modified:
            response['Last-Modified'] = last_modified

        return response


class VmServiceHandler:
    @staticmethod
    def get_user_perm_service(_id, user):
        """
        :raises: Error
        """
        service = ServiceManager().get_service_by_id(_id)
        if service is None:
            raise exceptions.ServiceNotExist()

        if not service.user_has_perm(user):
            raise exceptions.AccessDenied(message=_('你没有此服务的管理权限'))

        return service

    @staticmethod
    def get_private_quota(view, request, kwargs):
        """
        查询服务私有配额
        """
        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            quota = ServicePrivateQuotaManager().get_quota(service=service)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServicePrivateQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def change_private_quota(view, request, kwargs):
        """
        修改服务私有配额
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        data = serializer.validated_data
        private_ip_total = data.get('private_ip_total')
        public_ip_total = data.get('public_ip_total')
        vcpu_total = data.get('vcpu_total')
        ram_total = data.get('ram_total')
        disk_size_total = data.get('disk_size_total')

        try:
            quota = ServicePrivateQuotaManager().update(
                service=service, vcpus=vcpu_total, ram=ram_total, disk_size=disk_size_total,
                public_ip=public_ip_total, private_ip=private_ip_total, only_increase=True)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServicePrivateQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def get_share_quota(view, request, kwargs):
        """
        查询服务共享配额
        """
        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            quota = ServiceShareQuotaManager().get_quota(service=service)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServiceShareQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def change_share_quota(view, request, kwargs):
        """
        修改服务共享配额
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        data = serializer.validated_data
        private_ip_total = data.get('private_ip_total')
        public_ip_total = data.get('public_ip_total')
        vcpu_total = data.get('vcpu_total')
        ram_total = data.get('ram_total')
        disk_size_total = data.get('disk_size_total')

        try:
            quota = ServiceShareQuotaManager().update(
                service=service, vcpus=vcpu_total, ram=ram_total, disk_size=disk_size_total,
                public_ip=public_ip_total, private_ip=private_ip_total, only_increase=True)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServiceShareQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def list_services(view, request, kwargs):
        """
        list接入服务provider
        """
        center_id = request.query_params.get('center_id', None)
        service_qs = ServiceManager().filter_service(center_id=center_id)
        return view.paginate_service_response(request=request, qs=service_qs)

    @staticmethod
    def list_vo_services(view, request, kwargs):
        """
        list指定vo组有资源配额可用的服务provider
        """
        center_id = request.query_params.get('center_id', None)
        vo_id = kwargs.get('vo_id')
        try:
            vo, member = VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        service_qs = ServiceManager().filter_vo_service(vo=vo, center_id=center_id)
        return view.paginate_service_response(request=request, qs=service_qs)


class VoHandler:
    @staticmethod
    def list_vo(view, request, kwargs):
        _owner = request.query_params.get('owner', None)
        _member = request.query_params.get('member', None)
        if _owner is not None:
            _owner = True
        if _member is not None:
            _member = True

        try:
            queryset = VoManager().get_user_vo_queryset(user=request.user, owner=_owner, member=_member)
            paginator = view.pagination_class()
            vos = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = view.get_serializer(instance=vos, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create(view, request, kwargs):
        """
        创建一个组
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        name = data.get('name')
        company = data.get('company')
        description = data.get('description')

        try:
            vo = VoManager().create_vo(name=name, company=company, description=description, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=view.get_serializer(instance=vo).data)

    @staticmethod
    def delete_vo(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        try:
            VoManager().delete_vo(vo_id=vo_id, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        return Response(status=204)

    @staticmethod
    def update_vo(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        name = data.get('name')
        company = data.get('company')
        description = data.get('description')

        try:
            vo = VoManager().update_vo(vo_id=vo_id, admin_user=request.user, name=name,
                                       company=company, description=description)
            return Response(data=serializers.VoSerializer(instance=vo).data)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def vo_add_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data.get('usernames', [])
        try:
            success_members, failed_usernames = VoManager().add_members(
                vo_id=vo_id, usernames=usernames, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        members = serializers.VoMemberSerializer(success_members, many=True).data
        return Response(data={'success': members, 'failed': failed_usernames})

    @staticmethod
    def vo_list_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        try:
            vo, members = VoManager().get_vo_members_queryset(vo_id=vo_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        data = view.get_serializer(members, many=True).data
        return Response(data={
            'members': data, 'owner': {'id': vo.owner.id, 'username': vo.owner.username}})

    @staticmethod
    def vo_remove_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data.get('usernames', [])
        try:
            VoManager().remove_members(vo_id=vo_id, usernames=usernames, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        return Response(status=204)

    @staticmethod
    def vo_members_role(view, request, kwargs):
        member_id = kwargs.get('member_id')
        role = kwargs.get('role')
        if not role:
            raise exceptions.BadRequest(message=_('"role"的值无效'))

        try:
            member = VoMemberManager().change_member_role(
                member_id=member_id, role=role, admin_user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data=serializers.VoMemberSerializer(member).data)


class QuotaActivityHandler:
    @staticmethod
    def list_activities(view, request, kwargs):
        status = request.query_params.get('status', None)
        exclude_not_start = request.query_params.get('exclude-not-start', None)
        exclude_ended = request.query_params.get('exclude-ended', None)

        if status is not None and status not in QuotaActivityManager.MODEL.Status.values:
            return view.exception_response(exceptions.BadRequest(message=_('参数status的值无效')))

        if exclude_not_start is not None:
            exclude_not_start = True

        if exclude_ended is not None:
            exclude_ended = True

        queryset = QuotaActivityManager().filter_queryset(
            deleted=False, status=status, exclude_not_start=exclude_not_start, exclude_ended=exclude_ended)

        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(queryset, request=request, view=view)
            serializer = view.get_serializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def create_activity(view, request, kwargs):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        service_id = data.get('service_id')
        service = ServiceManager.get_service_by_id(_id=service_id)
        if service is None:
            return view.exception_response(exceptions.NotFound(
                message=_('云主机服务provider不存在')))

        if service.status != service.Status.ENABLE:
            return view.exception_response(exceptions.ConflictError(
                message=_('云主机服务provider不可用')))

        if not service.user_has_perm(request.user):
            return view.exception_response(exceptions.AccessDenied(
                message=_('你没有云主机服务provider的管理权限，无权为此服务创建活动')))

        try:
            qa = QuotaActivityManager().create_activity(data=data, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=view.get_serializer(instance=qa).data)

    @staticmethod
    def quota_activity_get(view, request, kwargs):
        """
        从配额活动领取配额
        """
        _id = kwargs.get(view.lookup_field)
        try:
            quota = QuotaActivityManager().activity_got_once(_id=_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'quota_id': quota.id})
