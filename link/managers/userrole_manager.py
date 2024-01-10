from link.models import LinkUserRole


class UserRoleWrapper:
    def __init__(self, user):
        self.user = user
        self._user_role = None

    @property
    def user_role(self):
        if self._user_role is None:
            self._user_role = self.get_user_link_role(user=self.user)
        return self._user_role

    def get_or_create_user_role(self):
        return self.get_user_link_role(self.user, create_not_exists=True)

    def refresh(self, is_lazy: bool = True):
        self._user_role = None
        if not is_lazy:
            return self.user_role

        return None

    @staticmethod
    def get_user_link_role(user, create_not_exists: bool = False):
        db_userrole = LinkUserRole.objects.select_related('user').filter(user_id=user.id).first()
        if db_userrole is None:
            db_userrole = LinkUserRole(user=user, is_admin=False, is_readonly=False)
            if create_not_exists:
                db_userrole.save(force_insert=True)

        return db_userrole

    def has_read_permission(self) -> bool:
        if self.user_role is None:
            return False
        return self.user_role.is_admin or self.user_role.is_readonly

    def has_write_permission(self) -> bool:
        if self.user_role is None:
            return False
        return self.user_role.is_admin
