from django.utils.translation import gettext as _
from django.utils import timezone as dj_timezone
from django.db.models import Q
from rest_framework.response import Response

from core import errors
from api.viewsets import NormalGenericViewSet, serializer_error_msg
from service.models import DataCenter as Organization
from ..managers import UserIpamRoleWrapper
from ..models import OrgVirtualObject
from .. import serializers


class OrgVirtObjHandler:
    def add_org_virt_obj(self, view: NormalGenericViewSet, request):
        try:
            data = self._add_org_obj_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        org = Organization.objects.filter(id=data['organization_id']).first()
        if org is None:
            return view.exception_response(
                errors.InvalidArgument(message=_('机构id无效，机构不存在')))

        ur_wrapper = UserIpamRoleWrapper(user=request.user)
        if not ur_wrapper.has_kjw_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有科技网IP管理功能的管理员权限')))

        try:
            ovo = OrgVirtualObject(
                name=data['name'], organization=org, remark=data['remark'], creation_time=dj_timezone.now())
            ovo.save(force_insert=True)
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

        ur_wrapper = UserIpamRoleWrapper(user=request.user)
        if not ur_wrapper.has_kjw_admin_readable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有科技网IP管理功能的管理员权限')))

        try:
            qs = OrgVirtualObject.objects.select_related('organization').order_by('-creation_time')
            if org_id:
                qs = qs.filter(organization_id=org_id)
            if search:
                qs = qs.filter(Q(name__icontains=search) | Q(remark__icontains=search))

            objs = view.paginate_queryset(qs)
            serializer = serializers.OrgVirtualObjectSimpleSerializer(instance=objs, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)
