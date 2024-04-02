from decimal import Decimal

from django.utils.translation import gettext as _
from django.db.models import Q
from django.db import transaction

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
        return VoManager.model.objects.select_related('owner').filter(id=vo_id, deleted=False).first()

    @staticmethod
    def check_read_perm(vo, user) -> VoMember or None:
        """
        检测用户是否有vo组的访问权限

        :return:
            None        # 用户是vo组的拥有者
            VoMember()  # 用户是vo组的管理员
            raise Error # 用户是vo组的普通组员，或者用户不属于vo组
        :raises: Error
        """
        if vo.owner_id == user.id:  # 组长
            return None

        member = VoMemberManager.get_member_by_filters(vo=vo, user=user)
        if member is None:
            raise errors.AccessDenied(message=_('你不属于此项目组，没有访问权限'))

        return member

    @staticmethod
    def check_manager_perm(vo, user) -> VoMember or None:
        """
        检测用户是否有vo组的管理权限

        :return:
            None        # 用户是vo组的拥有者
            VoMember()  # 用户是vo组的管理员
            raise Error # 用户是vo组的普通组员，或者用户不属于vo组
        :raises: Error
        """
        member = VoManager.check_read_perm(vo=vo, user=user)
        if member is None:
            return None

        if member.is_leader_role:
            return member

        raise errors.AccessDenied(message=_('你不是组管理员，没有组管理权限'))

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
            raise errors.VoNotExist(message=_('项目组不存在'))

        member = self.check_manager_perm(vo=vo, user=user)
        return vo, member

    def get_has_read_perm_vo(self, vo_id: str, user) -> (VirtualOrganization, VoMember):
        """
        查询用户有访问权限的vo

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

        member = self.check_read_perm(vo=vo, user=user)
        return vo, member

    @staticmethod
    def get_queryset():
        return VoManager.model.objects.select_related('owner').all()

    def get_no_delete_queryset(self):
        return self.get_queryset().filter(deleted=False)

    @staticmethod
    def get_user_vo_queryset(user, owner: bool = None, member: bool = None, name: str = None):
        """
        查询用户相关的组（组员或组拥有者）
        * owner和member同时为None时等同于同时为True

        :param user: 用户
        :param owner: True:查询包含作为组拥有者的组;
        :param member: True:查询包含作为组员的组;
        :param name: vo组名关键字查询
        """
        queryset = VirtualOrganization.objects.select_related('owner').filter(deleted=False)

        if owner and member:
            queryset = queryset.filter(Q(vomember__user=user) | Q(owner=user)).distinct()
        elif member:
            queryset = queryset.filter(vomember__user=user)
        elif owner:
            queryset = queryset.filter(owner=user)
        elif owner is None and member is None:
            queryset = queryset.filter(Q(vomember__user=user) | Q(owner=user)).distinct()
        else:
            queryset = queryset.none()

        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset

    @staticmethod
    def get_admin_vo_queryset(user: User, owner: bool = None, member: bool = None, name: str = None):
        """
        管理员查询组，只允许联邦管理员
        * owner和member同时为None时查询所有

        :param user: 用户
        :param owner: True:查询包含作为组拥有者的组;
        :param member: True:查询包含作为组员的组;
        :param name: vo组名关键字查询
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有联邦管理员权限'))

        queryset = VirtualOrganization.objects.select_related('owner').filter(deleted=False)

        if owner and member:
            queryset = queryset.filter(Q(vomember__user=user) | Q(owner=user)).distinct()
        elif member:
            queryset = queryset.filter(vomember__user=user)
        elif owner:
            queryset = queryset.filter(owner=user)

        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset

    def add_members(self, vo_id: str, usernames: list, admin_user) -> (list, list):
        """
        向组添加组成员

        :param vo_id: 组id
        :param usernames: 要添加的组成员用户名
        :param admin_user: 请求添加操作的用户，需要是组管理员权限
        :return:
            [VoMember(),], [{'username': 'xxx', 'message': 'xxx'},]     # 添加成功用户，失败的用户和失败原因

        :raises: Error
        """
        not_found_usernames = [u for u in usernames]
        vo, admin_member = self.get_has_manager_perm_vo(vo_id=vo_id, user=admin_user)
        if vo.owner.username in usernames:        # 组长，组拥有者
            raise errors.AccessDenied(message=_('你要添加的用户中不能包含组的拥有者（组长）'))

        users = User.objects.filter(username__in=usernames).all()

        failed_users = []
        success_members = []
        exists_member = VoMember.objects.filter(vo=vo, user__username__in=usernames).all()
        if (len(users) + len(exists_member)) > VirtualOrganization.MAX_NUMBER_OF_MEMBERS:
            raise errors.TooManyVoMember()

        exists_user_id_member_map = {m.user.id: m for m in exists_member}
        for user in users:
            if user.username in not_found_usernames:
                not_found_usernames.remove(user.username)   # 移除存在的，剩余的都是未找到的

            if user.id in exists_user_id_member_map:
                success_members.append(exists_user_id_member_map[user.id])
                continue

            member = VoMember(user=user, vo=vo, role=VoMember.Role.MEMBER,
                              inviter=admin_user.username, inviter_id=admin_user.id)
            try:
                member.save()
                success_members.append(member)
            except Exception as e:
                failed_users.append({'username': user.username, 'message': str(e)})

        for um in not_found_usernames:
            failed_users.append({'username': um, 'message': _('用户名不存在')})

        return success_members, failed_users

    def remove_members(self, vo_id: str, usernames: list, admin_user):
        """
        从组移出组成员

        :param vo_id: 组id
        :param usernames: 要移除的组成员用户名
        :param admin_user: 请求移除操作的用户，需要是组管理员权限
        :return:
            None

        :raises: Error
        """
        vo, admin_member = self.get_has_manager_perm_vo(vo_id=vo_id, user=admin_user)
        if vo.owner.username in usernames:        # 组长，组拥有者
            raise errors.AccessDenied(message=_('你要移出的用户中不能包含组的拥有者（组长）'))

        if admin_member and admin_member.is_leader_role:
            # 组管理员 不能移除 管理员
            if VoMember.objects.filter(vo=vo, role=VoMember.Role.LEADER,
                                       user__username__in=usernames).exists():
                raise errors.AccessDenied(message=_('你没有权限移除组管理员'))

        try:
            VoMember.objects.filter(vo=vo, user__username__in=usernames).delete()
        except Exception as exc:
            raise errors.Error(message=_('组长移除组员错误,') + str(exc))

    def get_vo_members_queryset(self, vo_id: str, user=None) -> tuple:
        """
        查询指定组的组员

        :param vo_id: 组id
        :param user: 用于权限检查，user必须是组员才有权限查询；默认None不检查权限

        :return: vo, Queryset()
        :raises: Error
        """
        vo = self.get_vo_by_id(vo_id=vo_id)
        if vo is None:
            raise errors.NotFound(message=_('项目组不存在'))
        if user is not None:
            if not vo.is_owner(user) and not vo.is_member(user):
                raise errors.AccessDenied(message='你不属于组，无权限查询组员信息')

        return vo, VoMemberManager().get_vo_members_queryset(vo_id)

    def create_vo(self, user, name: str, company: str, description: str):
        """
        创建一个vo组
        """
        vo = self.model(owner=user, name=name, company=company, description=description)
        try:
            vo.save()
        except Exception as exc:
            raise errors.Error.from_error(exc)

        return vo

    def update_vo(self, vo_id: str, admin_user, owner=None, name: str = None, company: str = None,
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
        vo, admin_member = self.get_has_manager_perm_vo(vo_id=vo_id, user=admin_user)
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
        from apps.app_wallet.managers.payment import PaymentManager
        vo, admin_member = self.get_has_manager_perm_vo(vo_id=vo_id, user=admin_user)
        if not vo.is_owner(admin_user):
            raise errors.AccessDenied(message=_('你不是组拥有者，你没有权限删除组'))

        if Server.objects.filter(vo=vo).exists():
            raise errors.ResourceNotCleanedUp(message=_('无法删除组，组内有云主机资源未清理'))

        vo_account = PaymentManager.get_vo_point_account(vo_id=vo_id)
        if vo_account.balance < Decimal('0'):
            raise errors.BalanceArrearage(message=_('无法删除组，组余额账户欠费'))

        try:
            vo.soft_delete()
        except Exception as exc:
            raise errors.Error.from_error(exc)

    def devolve_vo_owner_to_member(self, vo_id: str, member_id: str, owner):
        vo = VoManager().get_vo_by_id(vo_id=vo_id)
        if vo is None:
            raise errors.VoNotExist(message=_('项目组不存在'))

        member: VoMember = VoMember.objects.select_related('user').filter(id=member_id).first()
        if member is None:
            raise errors.TargetNotExist(message=_('指定组员不存在'))

        self._devolve_vo_owner(vo=vo, member=member, owner=owner)
        return vo

    def devolve_vo_owner_to_username(self, vo_id: str, username: str, owner):
        vo = VoManager().get_vo_by_id(vo_id=vo_id)
        if vo is None:
            raise errors.VoNotExist(message=_('项目组不存在'))

        member = VoMember.objects.filter(vo_id=vo.id, user__username=username).first()
        if member is None:
            raise errors.TargetNotExist(message=_('指定组员不存在'))

        self._devolve_vo_owner(vo=vo, member=member, owner=owner)
        return vo

    @staticmethod
    def _devolve_vo_owner(vo: VirtualOrganization, member: VoMember, owner):
        if not vo.is_owner(owner):
            raise errors.AccessDenied(message=_('你不是组拥有者，你没有移交组长的权限'))

        if member.vo_id != vo.id:
            raise errors.ConflictError(message=_('指定组员不属于项目组'))

        with transaction.atomic():
            owner = vo.owner
            vo.owner = member.user
            vo.save(update_fields=['owner'])

            member.user = owner
            member.role = VoMember.Role.LEADER.value
            member.save(update_fields=['user', 'role'])

    @staticmethod
    def has_vo_permission(vo_id, user, read_only: bool = True, raise_exc: bool = True):
        """
        是否有vo组的权限

        :raises: AccessDenied
        """
        try:
            if read_only:
                VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
            else:
                VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=user)
        except errors.Error as exc:
            if raise_exc:
                raise errors.AccessDenied(message=exc.message)

            return False

        return True


class VoMemberManager:
    model = VoMember

    @staticmethod
    def get_member_by_filters(**filters) -> VoMember:
        """
        :return: VoMember() or None
        """
        return VoMemberManager.model.objects.select_related('vo').filter(**filters).first()

    @staticmethod
    def get_queryset():
        return VoMemberManager.model.objects.all()

    def get_vo_members_queryset(self, vo_id: str):
        qs = self.get_queryset()
        return qs.select_related('user').filter(vo=vo_id)

    def change_member_role(self, member_id: str, role: str, admin_user) -> VoMember:
        """
        修改组员角色

        * 组拥有者（组长）可以修改任何组员角色；组管理员

        :raises: Error
        """
        if role not in VoMember.Role.values:
            raise errors.InvalidArgument(message=_('The value of "role" is invalid.'))

        member = self.get_member_by_filters(id=member_id)
        if member is None:
            raise errors.NotFound(message=_('组员不存在'))

        if not member.vo.is_owner(admin_user):
            raise errors.AccessDenied(message=_('你不是组的拥有者，无权限修改组员的角色'))

        if member.role == role:
            return member

        try:
            member.role = role
            member.save(update_fields=['role'])
        except Exception as exc:
            raise errors.Error.from_error(exc)

        return member
