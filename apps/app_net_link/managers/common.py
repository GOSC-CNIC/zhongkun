from django.utils import timezone as dj_timezone

from apps.app_net_link.models import NetLinkUserRole


class NetLinkUserRoleWrapper:
    def __init__(self, user):
        self.user = user
        self._user_role = None  # link user role instance

    @property
    def user_role(self) -> NetLinkUserRole:
        if self._user_role is None:
            self._user_role = self.get_user_link_role(user=self.user)

        return self._user_role

    @user_role.setter
    def user_role(self, val: NetLinkUserRole):
        self._user_role = val

    def refresh(self):
        self._user_role = None
        return self.user_role

    def get_or_create_user_role(self):
        return self.get_user_link_role(self.user, create_not_exists=True)

    @staticmethod
    def get_user_link_role(user, create_not_exists: bool = False):
        urole = NetLinkUserRole.objects.select_related('user').filter(user_id=user.id).first()
        if urole:
            return urole

        nt = dj_timezone.now()
        urole = NetLinkUserRole(
            user=user, is_link_admin=False, is_link_readonly=False,
            creation_time=nt, update_time=nt
        )
        if create_not_exists:
            urole.save(force_insert=True)

        return urole

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
