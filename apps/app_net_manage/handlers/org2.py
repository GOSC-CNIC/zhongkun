from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from apps.api.viewsets import NormalGenericViewSet, serializer_error_msg
from apps.app_service.models import DataCenter as Organization
from apps.app_net_manage.managers import NetManageUserRoleWrapper, OrgVirtualObjectManager, ContactPersonManager
from apps.app_net_manage import serializers as common_serializers


class PermissionMixin:
    @staticmethod
    def has_write_permission(user):
        roler = NetManageUserRoleWrapper(user=user)
        return roler.is_admin()

    @staticmethod
    def has_read_permission(user):
        roler = NetManageUserRoleWrapper(user=user)
        return roler.is_admin()


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
                errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            ovo = OrgVirtualObjectManager.create_org_virt_obj(
                name=data['name'], org=org, remark=data['remark']
            )
            serializer = common_serializers.OrgVirtualObjectSimpleSerializer(instance=ovo)
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
                errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            ovo = OrgVirtualObjectManager.update_org_virt_obj(
                _id=kwargs[view.lookup_field], name=data['name'], org=org, remark=data['remark']
            )
            serializer = common_serializers.OrgVirtualObjectSimpleSerializer(instance=ovo)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_org_virt_obj(view: NormalGenericViewSet, request):
        org_id = request.query_params.get('org_id')
        search = request.query_params.get('search')

        # if not OrgVirtObjHandler.has_read_permission(request.user):
        #     return view.exception_response(
        #         errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            qs = OrgVirtualObjectManager.filter_queryset(org_id=org_id, search=search)
            objs = view.paginate_queryset(qs)
            serializer = common_serializers.OrgVirtualObjectSimpleSerializer(instance=objs, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    def detail_org_virt_obj(self, view: NormalGenericViewSet, request, kwargs):
        if not self.has_read_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            ovo = OrgVirtualObjectManager.get_org_virt_obj(_id=kwargs[view.lookup_field])
            if ovo is None:
                raise errors.TargetNotExist(message=_('机构二级不存在'))

            serializer = common_serializers.OrgVirtualObjectSimpleSerializer(instance=ovo)
            data = serializer.data
            contacts = ovo.contacts.all()
            data['contacts'] = common_serializers.ContactPersonSerializer(contacts, many=True).data
            return Response(data=data)
        except Exception as exc:
            return view.exception_response(exc)

    def add_contacts(self, view: NormalGenericViewSet, request, kwargs):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(errors.BadRequest(msg))

        contact_ids = serializer.validated_data['contact_ids']
        if not contact_ids:
            return view.exception_response(
                errors.InvalidArgument(message=_('没有指定联系人')))

        if not self.has_write_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            ovo = OrgVirtualObjectManager.get_org_virt_obj(_id=kwargs[view.lookup_field])
            if ovo is None:
                raise errors.TargetNotExist(message=_('机构二级不存在'))

            OrgVirtualObjectManager.add_contacts_for_ovo(ovo=ovo, contact_ids=contact_ids)
            data = common_serializers.OrgVirtualObjectSimpleSerializer(instance=ovo).data
            contacts = ovo.contacts.all()
            data['contacts'] = common_serializers.ContactPersonSerializer(contacts, many=True).data
            return Response(data=data)
        except errors.Error as exc:
            return view.exception_response(exc)

    def remove_contacts(self, view: NormalGenericViewSet, request, kwargs):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(errors.BadRequest(msg))

        contact_ids = serializer.validated_data['contact_ids']
        if not contact_ids:
            return view.exception_response(
                errors.InvalidArgument(message=_('没有指定联系人')))

        if not self.has_write_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            ovo = OrgVirtualObjectManager.get_org_virt_obj(_id=kwargs[view.lookup_field])
            if ovo is None:
                raise errors.TargetNotExist(message=_('机构二级不存在'))

            OrgVirtualObjectManager.remove_admins_from_ovo(ovo=ovo, contact_ids=contact_ids)
            data = common_serializers.OrgVirtualObjectSimpleSerializer(instance=ovo).data
            contacts = ovo.contacts.all()
            data['contacts'] = common_serializers.ContactPersonSerializer(contacts, many=True).data
            return Response(data=data)
        except errors.Error as exc:
            return view.exception_response(exc)


class ContactsHandler(PermissionMixin):
    def add_contact_person(self, view: NormalGenericViewSet, request):
        try:
            data = self._add_contacts_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        if not self.has_write_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            person = ContactPersonManager.create_contact_person(
                name=data['name'], telephone=data['telephone'],
                email=data['email'], address=data['address'], remarks=data['remarks']
            )
            serializer = common_serializers.ContactPersonSerializer(instance=person)
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
                errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            person = ContactPersonManager.update_contact_person(
                _id=kwargs[view.lookup_field], name=data['name'], telephone=data['telephone'],
                email=data['email'], address=data['address'], remarks=data['remarks']
            )
            serializer = common_serializers.ContactPersonSerializer(instance=person)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_contact_person(view: NormalGenericViewSet, request):
        search = request.query_params.get('search')

        if not ContactsHandler.has_read_permission(request.user):
            return view.exception_response(
                errors.AccessDenied(message=_('你没有管理员权限')))

        try:
            qs = ContactPersonManager.get_contacts_qs(search=search)
            objs = view.paginate_queryset(qs)
            serializer = common_serializers.ContactPersonSerializer(instance=objs, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)
