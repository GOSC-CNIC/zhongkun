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
        return LinkUserRole.objects.select_related('user').filter(user_id=user.id).first()

    def has_read_permission(self) -> bool:
        if self.user_role is None:
            return False
        return self.user_role.is_admin or self.user_role.is_readonly

    def has_write_permission(self) -> bool:
        if self.user_role is None:
            return False
        return self.user_role.is_admin
