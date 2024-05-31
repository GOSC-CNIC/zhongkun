from django.utils import timezone as dj_timezone

from apps.app_net_ipam.models import NetIPamUserRole


class NetIPamUserRoleWrapper:
    def __init__(self, user):
        self.user = user
        self._user_role = None  # ipam user role instance
        self._org_ids = None    # 用户是机构管理员的所有机构id list

    @property
    def user_role(self) -> NetIPamUserRole:
        if self._user_role is None:
            self._user_role = self.get_user_net_ipam_role(user=self.user)

        return self._user_role

    @user_role.setter
    def user_role(self, val: NetIPamUserRole):
        self._user_role = val

    def refresh(self):
        self._user_role = None
        return self.user_role

    def get_or_create_user_role(self):
        return self.get_user_net_ipam_role(self.user, create_not_exists=True)

    @staticmethod
    def get_user_net_ipam_role(user, create_not_exists: bool = False):
        urole = NetIPamUserRole.objects.select_related('user').filter(user_id=user.id).first()
        if urole:
            return urole

        nt = dj_timezone.now()
        urole = NetIPamUserRole(
            user=user, is_ipam_admin=False, is_ipam_readonly=False,
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
