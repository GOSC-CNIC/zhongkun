from typing import Union
from datetime import datetime

from django.utils.translation import gettext as _
from link.models import LinkUserRole


class UserRoleWrapper:
    def __init__(self, user):
        self.user = user
        self._user_role = None

    @property
    def user_role(self):
        if not self._user_role:
            self._user_role = self.get_user_link_role(user=self.user)
        return self._user_role

    @staticmethod
    def get_user_link_role(user):
        urole = LinkUserRole.objects.select_related('user').filter(user_id=user.id).first()
        if urole:
            return urole
        urole = LinkUserRole(user=user, is_admin=False, is_readonly=False)
        urole.save(force_insert=True)
        return urole

    def has_read_permission(self) -> bool:
        return self.user_role.is_admin or self.user_role.is_readonly

    def has_write_permission(self) -> bool:
        return self.user_role.is_admin

    def add_read_permission(self):
        self.user_role.is_readonly = True
        self.user_role.save(force_update=True)

    def add_write_permission(self) -> bool:
        self.user_role.is_admin = True
        self.user_role.save(force_update=True)
