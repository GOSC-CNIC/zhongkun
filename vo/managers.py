from django.utils.translation import gettext as _

from servers.models import Server
from core import errors
from users.models import UserProfile as User
from .models import VirtualOrganization, VoMember


class VoManager:
    model = VirtualOrganization

    @staticmethod
    def get_vo_by_id(vo_id: str) -> VirtualOrganization:
        """
        :return:
            VirtualOrganization() or None
        """
        return VoManager.model.objects.select_related('user').filter(id=vo_id, deleted=False).first()

    def get_has_manager_perm_vo(self, vo_id: str, user) -> (VirtualOrganization, VoMember):
        """
        查询用户有管理员权限的vo

        :return:
            (
                VirtualOrganization(),  # 组实例
                VoMember() or None      # user对应的组员实例; None(user是组拥有者)
            )

        :raises: Error
        """
        vo = self.get_vo_by_id(vo_id=vo_id)
        if vo is None:
            raise errors.NotFound(message=_('项目组不存在'))

        if vo.owner_id == user.id:      # 组长
            return vo, None

        member = VoMemberManager.get_member_by_filters(vo=vo, user=user)
        if member is None:
            raise errors.AccessDenied(message=_('你不属于此项目组，没有访问权限'))

        if member.is_leader_role:
            return vo, member

        raise errors.AccessDenied(message=_('你不是组管理员，没有组管理权限'))


    @staticmethod
    def get_queryset():
        return VoManager.model.objects.all()

    def get_no_delete_queryset(self):
        return self.get_queryset().filter(deleted=False)

    def add_members(self, vo_id: str, usernames: list, admin_user):
        """
        向组添加组成员

        :param vo_id: 组id
        :param usernames: 要添加的组成员用户名
        :param admin_user: 请求添加操作的用户，需要是组管理员权限
        :return:
            [{'username': 'xxx', 'message': 'xxx'},]     # 添加失败的用户和失败原因

        :raises: Error
        """
        not_found_usernames = [u for u in usernames]
        vo, _ = self.get_has_manager_perm_vo(vo_id=vo_id, user=admin_user)
        users = User.objects.filter(username__in=usernames).all()
        failed_users = []

        exists_member = VoMember.objects.filter(vo=vo, user__username__in=usernames).all()
        exists_user_ids = [m.user.id for m in exists_member]
        exists_user_ids.append(vo.owner_id)     # 组长，组拥有者

        for user in users:
            if user.username in not_found_usernames:
                not_found_usernames.remove(user.username)   # 移除存在的，剩余的都是未找到的

            if user.id in exists_user_ids:
                continue

            member = VoMember(user=user, vo=vo, role=VoMember.Role.MEMBER,
                              inviter=admin_user.username, inviter_id=admin_user.id)
            try:
                member.save()
            except Exception as e:
                failed_users.append({'username': user.username, 'message': str(e)})

        for um in not_found_usernames:
            failed_users.append({'username': um, 'message': _('用户名不存在')})

        return failed_users

    def remove_members(self, vo_id: str, usernames: list, admin_user):
        """
        从组移除组成员

        :param vo_id: 组id
        :param usernames: 要移除的组成员用户名
        :param admin_user: 请求移除操作的用户，需要是组管理员权限
        :return:
            None

        :raises: Error
        """
        vo, admin_member = self.get_has_manager_perm_vo(vo_id=vo_id, user=admin_user)
        if admin_member.is_leader_role:
            # 组管理员 不能移除 管理员
            if VoMember.objects.filter(vo=vo, role=VoMember.Role.LEADER,
                                       user__username__in=usernames).exits():
                raise errors.AccessDenied(message=_('你没有权限移除组管理员'))

        try:
            VoMember.objects.filter(vo=vo, user__username__in=usernames).delete()
        except Exception as exc:
            raise errors.Error(message=_('组长移除组员错误,') + str(exc))

    def get_vo_members_queryset(self, vo_id: str):
        """
        查询指定组的组员

        :return: Queryset()
        :raises: Error
        """
        vo = self.get_vo_by_id(vo_id=vo_id)
        if vo is None:
            raise errors.NotFound(message=_('项目组不存在'))

        return vo.members.all()

    def create_vo(self, user, name:str, company: str, description: str):
        """
        创建一个vo组
        """
        vo = self.model(owner=user, name=name, company=company, description=description)
        try:
            vo.save()
        except Exception as exc:
            raise errors.Error.from_error(exc)

        return vo

    def update_vo(self, vo_id: str, admin_user, owner=None, name: str = None, company: str=None,
                  description: str = None) -> VirtualOrganization:
        """
        修改组信息

        :param vo_id: 组id
        :param admin_user: 请求修改的用户
        :param owner: 把组拥有权转给此用户；默认None，忽略
        :param name: 新的组名称；默认None，忽略
        :param company: 新的单位名称；默认None，忽略
        :param description: 新的组描述信息；默认None，忽略
        :raises: Error
        """
        vo, _ = self.get_has_manager_perm_vo(vo_id=vo_id, user=admin_user)
        update_fields = []
        if owner is not None:
            if not vo.is_owner(admin_user):
                raise errors.AccessDenied(message=_('你不是组拥有者，无权限更换组拥有者'))

            vo.owner = owner
            update_fields.append('owner')

        if name:
            vo.name = name
            update_fields.append('name')

        if company:
            vo.company = company
            update_fields.append('company')

        if description:
            vo.description = description
            update_fields.append('description')

        if not update_fields:
            return vo

        try:
            vo.save(update_fields=update_fields)
        except Exception as exc:
            raise errors.Error.from_error(exc)

        return vo

    def delete_vo(self, vo_id: str, admin_user) -> None:
        """
        删除组

        :param vo_id: 组id
        :param admin_user: 请求修改的用户

        :raises: Error
        """
        vo, _ = self.get_has_manager_perm_vo(vo_id=vo_id, user=admin_user)
        if not vo.is_owner(admin_user):
            raise errors.AccessDenied(message=_('你不是组拥有者，你去权限删除组'))

        if Server.objects.filter(vo=vo).exists():
            raise errors.ResourceNotCleanedUp(message=_('无法删除组，组内有云主机资源未清理'))

        try:
            vo.delete()
        except Exception as exc:
            raise errors.Error.from_error(exc)


class VoMemberManager:
    model = VoMember

    @staticmethod
    def get_member_by_filters(**filters) -> VoMember:
        """
        :return: VoMember() or None
        """
        return VoMemberManager.model.objects.filter(**filters).first()

    @staticmethod
    def get_queryset():
        return VoManager.model.objects.all()
