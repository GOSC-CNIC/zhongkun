from typing import List
from datetime import datetime

from django.db.models import Q
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError

from core import errors
from service.models import DataCenter as Organization
from apps.app_netbox.models import (
    NetBoxUserRole, OrgVirtualObject, ContactPerson
)


class NetBoxUserRoleWrapper:
    def __init__(self, user):
        self.user = user
        self._user_role = None  # ipam user role instance
        self._org_ids = None    # 用户是机构管理员的所有机构id list

    @property
    def user_role(self) -> NetBoxUserRole:
        if self._user_role is None:
            self._user_role = self.get_user_netbox_role(user=self.user)

        return self._user_role

    @user_role.setter
    def user_role(self, val: NetBoxUserRole):
        self._user_role = val

    def refresh(self):
        self._user_role = None
        return self.user_role

    def get_or_create_user_role(self):
        return self.get_user_netbox_role(self.user, create_not_exists=True)

    @staticmethod
    def get_user_netbox_role(user, create_not_exists: bool = False):
        urole = NetBoxUserRole.objects.select_related('user').filter(user_id=user.id).first()
        if urole:
            return urole

        nt = dj_timezone.now()
        urole = NetBoxUserRole(
            user=user, is_ipam_admin=False, is_ipam_readonly=False, is_link_admin=False, is_link_readonly=False,
            creation_time=nt, update_time=nt
        )
        if create_not_exists:
            urole.save(force_insert=True)

        return urole

    def has_ipam_admin_readable(self) -> bool:
        """是否有IP管理员读权限"""
        role = self.user_role
        if role.is_ipam_admin:
            return True

        if role.is_ipam_readonly:
            return True

        return False

    def has_ipam_admin_writable(self) -> bool:
        """是否有IP管理员写权限"""
        role = self.user_role
        if role.is_ipam_admin:
            return True

        return False

    def set_ipam_admin(self, val: bool = True, update_db: bool = True):
        self.user_role.is_ipam_admin = val
        if update_db:
            self.user_role.save(update_fields=['is_ipam_admin'])

    def set_ipam_readonly(self, val: bool = True, update_db: bool = True):
        self.user_role.is_ipam_readonly = val
        if update_db:
            self.user_role.save(update_fields=['is_ipam_readonly'])

    def is_ipam_admin_of_org(self, org_id: str) -> bool:
        """
        是否是指定机构的机构IP管理员
        """
        return self.user_role.organizations.filter(id=org_id).exists()

    def get_user_ipam_org_ids(self, refresh: bool = False):
        """
        用户有IP管理员权限的所有机构id
        """
        if self._org_ids is None or refresh:
            self._org_ids = self.user_role.organizations.values_list('id', flat=True)

        return self._org_ids

    def has_link_read_permission(self) -> bool:
        if self.user_role is None:
            return False

        return self.user_role.is_link_admin or self.user_role.is_link_readonly

    def has_link_write_permission(self) -> bool:
        if self.user_role is None:
            return False

        return self.user_role.is_link_admin

    def set_link_admin(self, val: bool = True, update_db: bool = True):
        self.user_role.is_link_admin = val
        if update_db:
            self.user_role.save(update_fields=['is_link_admin'])

    def set_link_readonly(self, val: bool = True, update_db: bool = True):
        self.user_role.is_link_readonly = val
        if update_db:
            self.user_role.save(update_fields=['is_link_readonly'])


class OrgVirtualObjectManager:
    """
    机构二级对象
    """
    @staticmethod
    def get_org_virt_obj(_id: str) -> OrgVirtualObject:
        return OrgVirtualObject.objects.filter(id=_id).first()

    @staticmethod
    def create_org_virt_obj(name: str, org: Organization, remark: str = '', creation_time: datetime = None):
        obj = OrgVirtualObject(
            name=name, organization=org, remark=remark,
            creation_time=creation_time if creation_time else dj_timezone.now()
        )
        try:
            obj.clean()
        except ValidationError as exc:
            if exc.code == errors.TargetAlreadyExists().code:
                raise errors.TargetAlreadyExists(message=str(exc))

            raise errors.InvalidArgument(message=str(exc))

        obj.save(force_insert=True)
        return obj

    @staticmethod
    def update_org_virt_obj(_id: str, name: str, org: Organization, remark: str):
        obj = OrgVirtualObjectManager.get_org_virt_obj(_id=_id)
        if obj is None:
            raise errors.TargetNotExist(message=_('机构二级对象不存在'))

        if obj.name == name and obj.organization_id == org.id and obj.remark == remark:
            return obj

        obj.name = name
        obj.organization = org
        obj.organization_id = org.id
        obj.remark = remark
        try:
            obj.clean()
        except ValidationError as exc:
            if exc.code == errors.TargetAlreadyExists().code:
                raise errors.TargetAlreadyExists(message=str(exc))

            raise errors.InvalidArgument(message=str(exc))

        obj.save(update_fields=['name', 'organization_id', 'remark'])
        return obj

    @staticmethod
    def filter_queryset(org_id, search):
        qs = OrgVirtualObject.objects.select_related('organization')
        if org_id:
            qs = qs.filter(organization_id=org_id)

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(remark__icontains=search) | Q(
                organization__name__icontains=search))

        return qs.order_by('-creation_time')

    @staticmethod
    def _validate_contact_ids(contact_ids: list) -> List[ContactPerson]:
        if not contact_ids:
            return []

        contact_id_set = set(contact_ids)
        if len(contact_id_set) != len(contact_ids):
            raise errors.InvalidArgument(message=_('提交的联系人列表中存在重复的ID'))

        contact_ids = list(contact_id_set)
        if len(contact_ids) == 1:
            cps = ContactPerson.objects.filter(id=contact_ids[0])
        else:
            cps = ContactPerson.objects.filter(id__in=contact_ids)

        cps = list(cps)
        if len(cps) != len(contact_id_set):
            exists_contact_id_set = {u.id for u in cps}
            not_exists_contact_ids = contact_id_set.difference(exists_contact_id_set)
            raise errors.InvalidArgument(message=_('指定的联系人ID不存在：') + '' + '、'.join(not_exists_contact_ids))

        return cps

    @staticmethod
    def add_contacts_for_ovo(ovo: OrgVirtualObject, contact_ids: list):
        cps = OrgVirtualObjectManager._validate_contact_ids(contact_ids=contact_ids)
        if not cps:
            return ovo

        ovo.contacts.add(*cps)  # 底层不会重复添加已存在的
        return ovo

    @staticmethod
    def remove_admins_from_ovo(ovo: OrgVirtualObject, contact_ids: list):
        cps = OrgVirtualObjectManager._validate_contact_ids(contact_ids=contact_ids)
        if not cps:
            return ovo

        ovo.contacts.remove(*cps)
        return ovo


class ContactPersonManager:
    @staticmethod
    def create_contact_person(
            name: str, telephone: str, email: str, address: str, remarks: str
    ):
        nt = dj_timezone.now()
        cp = ContactPerson(
            name=name, telephone=telephone, email=email, address=address, remarks=remarks,
            creation_time=nt, update_time=nt
        )
        try:
            cp.clean()
        except ValidationError as exc:
            err = getattr(exc, 'error', None)
            if err is not None and isinstance(err, errors.Error):
                raise err

            raise errors.InvalidArgument(message=str(exc))

        cp.save(force_insert=True)
        return cp

    @staticmethod
    def update_contact_person(
            _id: str, name: str, telephone: str, email: str, address: str, remarks: str
    ):
        cp = ContactPerson.objects.filter(id=_id).first()
        if cp is None:
            raise errors.TargetNotExist(message=_('联系人记录不存在'))

        cp.name = name
        cp.telephone = telephone
        cp.email = email
        cp.address = address
        cp.remarks = remarks
        cp.update_time = dj_timezone.now()
        try:
            cp.clean()
        except ValidationError as exc:
            err = getattr(exc, 'error', None)
            if err is not None and isinstance(err, errors.Error):
                raise err

            raise errors.InvalidArgument(message=str(exc))

        cp.save(force_update=True)
        return cp

    @staticmethod
    def get_contacts_qs(search: str = None):
        qs = ContactPerson.objects.all()

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(telephone__icontains=search) | Q(email__icontains=search))

        return qs.order_by('-creation_time')
