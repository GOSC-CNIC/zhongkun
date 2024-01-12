from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from api.viewsets import NormalGenericViewSet, serializer_error_msg
from service.models import DataCenter as Organization
from link.managers.userrole_manager import UserRoleWrapper as LinkUserRoleWrapper
from ..managers import UserIpamRoleWrapper, OrgVirtualObjectManager, ContactPersonManager
from .. import serializers


class PermissionMixin:
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


class OrgVirtObjHandler(PermissionMixin):
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

    def update_org_virt_obj(self, view: NormalGenericViewSet, request, kwargs):
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
            ovo = OrgVirtualObjectManager.update_org_virt_obj(
                _id=kwargs[view.lookup_field], name=data['name'], org=org, remark=data['remark']
            )
            serializer = serializers.OrgVirtualObjectSimpleSerializer(instance=ovo)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

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

    def detail_org_virt_obj(self, view: NormalGenericViewSet, request, kwargs):
        if not self.has_read_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理或者链路管理功能的管理员权限')))

        try:
            ovo = OrgVirtualObjectManager.get_org_virt_obj(_id=kwargs[view.lookup_field])
            if ovo is None:
                raise errors.TargetNotExist(message=_('机构二级不存在'))

            serializer = serializers.OrgVirtualObjectSimpleSerializer(instance=ovo)
            data = serializer.data
            contacts = ovo.contacts.all()
            data['contacts'] = serializers.ContactPersonSerializer(contacts, many=True).data
            return Response(data=data)
        except Exception as exc:
            return view.exception_response(exc)


class ContactsHandler(PermissionMixin):
    def add_contact_person(self, view: NormalGenericViewSet, request):
        try:
            data = self._add_contacts_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        if not self.has_write_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理或者链路管理功能的管理员权限')))

        try:
            person = ContactPersonManager.create_contact_person(
                name=data['name'], telephone=data['telephone'],
                email=data['email'], address=data['address'], remarks=data['remarks']
            )
            serializer = serializers.ContactPersonSerializer(instance=person)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _add_contacts_validate_params(view: NormalGenericViewSet, request):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'name' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('姓名无效。') + s_errors['name'][0])
            elif 'telephone' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('电话无效。') + s_errors['telephone'][0])
            elif 'remarks' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('备注无效。') + s_errors['remarks'][0])
            elif 'email' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('邮箱地址无效。') + s_errors['email'][0])
            else:
                msg = serializer_error_msg(s_errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        if not serializer.validated_data['name']:
            raise errors.InvalidArgument(message=_('必须提交一个有效的联系人姓名'))

        if not serializer.validated_data['telephone']:
            raise errors.InvalidArgument(message=_('必须提交联系人电话'))

        return serializer.validated_data

    def update_contact_person(self, view: NormalGenericViewSet, request, kwargs):
        try:
            data = self._add_contacts_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        if not self.has_write_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理或者链路管理功能的管理员权限')))

        try:
            person = ContactPersonManager.update_contact_person(
                _id=kwargs[view.lookup_field], name=data['name'], telephone=data['telephone'],
                email=data['email'], address=data['address'], remarks=data['remarks']
            )
            serializer = serializers.ContactPersonSerializer(instance=person)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_contact_person(view: NormalGenericViewSet, request):
        search = request.query_params.get('search')

        if not ContactsHandler.has_read_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有科技网IP管理或者链路管理功能的管理员权限')))

        try:
            qs = ContactPersonManager.get_contacts_qs(search=search)
            objs = view.paginate_queryset(qs)
            serializer = serializers.ContactPersonSerializer(instance=objs, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)
