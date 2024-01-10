from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from api.viewsets import NormalGenericViewSet, serializer_error_msg
from service.models import DataCenter as Organization
from link.managers.userrole_manager import UserRoleWrapper as LinkUserRoleWrapper
from ..managers import UserIpamRoleWrapper, OrgVirtualObjectManager
from .. import serializers


class OrgVirtObjHandler:
    @staticmethod
    def has_write_permission(user):
        ipam_roler = UserIpamRoleWrapper(user=user)
        if ipam_roler.has_kjw_admin_writable():
            return True

        link_roler = LinkUserRoleWrapper(user=user)
        if link_roler.has_write_permission():
            return True

        return False

    @staticmethod
    def has_read_permission(user):
        ipam_roler = UserIpamRoleWrapper(user=user)
        if ipam_roler.has_kjw_admin_readable():
            return True

        link_roler = LinkUserRoleWrapper(user=user)
        if link_roler.has_read_permission():
            return True

        return False

    def add_org_virt_obj(self, view: NormalGenericViewSet, request):
        try:
            data = self._add_org_obj_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        org = Organization.objects.filter(id=data['organization_id']).first()
        if org is None:
            return view.exception_response(
                errors.InvalidArgument(message=_('机构id无效，机构不存在')))

        if not self.has_write_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理或者链路管理功能的管理员权限')))

        try:
            ovo = OrgVirtualObjectManager.get_org_virt_obj(name=data['name'], org_id=org.id)
            if ovo:
                raise errors.TargetAlreadyExists(message=_('同名的机构二级对象已存在'))

            ovo = OrgVirtualObjectManager.create_org_virt_obj(
                name=data['name'], org=org, remark=data['remark']
            )
            serializer = serializers.OrgVirtualObjectSimpleSerializer(instance=ovo)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _add_org_obj_validate_params(view: NormalGenericViewSet, request):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'name' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('名称无效。') + s_errors['name'][0])
            elif 'organization_id' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('机构id无效。') + s_errors['organization_id'][0])
            elif 'remark' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('备注无效。') + s_errors['remark'][0])
            else:
                msg = serializer_error_msg(s_errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        return serializer.validated_data

    @staticmethod
    def list_org_virt_obj(view: NormalGenericViewSet, request):
        org_id = request.query_params.get('org_id')
        search = request.query_params.get('search')

        if not OrgVirtObjHandler.has_read_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有科技网IP管理或者链路管理功能的管理员权限')))

        try:
            qs = OrgVirtualObjectManager.filter_queryset(org_id=org_id, search=search)
            objs = view.paginate_queryset(qs)
            serializer = serializers.OrgVirtualObjectSimpleSerializer(instance=objs, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)
