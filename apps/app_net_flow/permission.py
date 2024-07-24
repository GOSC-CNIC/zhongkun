from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import Menu2Chart
from apps.app_net_flow.models import Menu2Member
from apps.app_net_flow.models import GlobalAdminModel
from apps.app_net_manage.permissions import NetIPRestrictor


class NetFlowAPIIPRestrictor(NetIPRestrictor):
    """
    流量模块 IP 白名单
    """
    pass


class PermissionManager(object):
    def __init__(self, request):
        self.request = request
        self.global_role = GlobalAdminModel.objects.filter(member=request.user).values_list('role', flat=True).first()
        self.relation = MenuModel.objects.values('id', 'father_id')
        self.relation_mapping = {_.get('id'): _.get('father_id') for _ in self.relation}
        self.group_role_mapping = self._get_group_role_mapping()

    def is_global_super_admin(self):
        """
        是否是流量模块超级管理员
        """
        return self.global_role == GlobalAdminModel.Roles.SUPER_ADMIN.value

    def is_global_ops_admin(self):
        """
        是否是流量模块运维管理员
        """
        return self.global_role == GlobalAdminModel.Roles.ADMIN.value

    def is_global_super_admin_or_ops_admin(self):
        """
        是否是流量模块全局管理员：
            超级管理员、运维管理员
        """
        return self.is_global_super_admin() or self.is_global_ops_admin()

    def is_branch_relationship(self, node1, node2):
        """
        判断两个节点是否在同一个分支
        """
        if node1.get('level') < node2.get('level'):
            parent, child = node1, node2
        else:
            parent, child = node2, node1
        return self.is_parent_or_self(parent.get('id'), child.get('id'))

    def is_parent_or_self(self, pid, cid):
        if pid == cid:
            return True
        father = self.relation_mapping.get(cid)
        while father:
            if pid == father:
                return True
            father = self.relation_mapping.get(father)

    def has_group_admin_permission(self, target_group_id: str):
        """
        具有当前组的管理权限
        """
        role = self.group_role_mapping.get(target_group_id)
        return role == Menu2Member.Roles.GROUP_ADMIN.value

    def has_group_permission(self, target_group_id: str):
        """
        具有当前组的访问权限
        """
        return self.group_role_mapping.get(target_group_id)

    def generate_group_tree(self, father, node_list):
        result = []
        for node in node_list:
            # 当前节点不是子节点
            if node['father_id'] != father:
                continue
            # 是否有当前组的管理权限
            if self.is_global_super_admin():
                node['admin'] = True
            elif self.has_group_admin_permission(node.get('id')):
                node['admin'] = True
            else:
                node['admin'] = False
            node['sub_categories'] = self.generate_group_tree(node.get('id'), node_list)
            node.pop('_state', '')
            result.append(node)
        return result

    def get_user_role(self):
        """
        查询当前用户的角色
            super-admin    流量模块超级管理员
            admin          流量模块运维管理员
            group-admin   流量模块组管理员
            ordinary      流量模块组员
        """
        # 超级管理员
        if self.is_global_super_admin():
            return GlobalAdminModel.Roles.SUPER_ADMIN.value
        # 运维管理员
        if self.is_global_ops_admin():
            return GlobalAdminModel.Roles.ADMIN.value
        # 组管理员
        if Menu2Member.Roles.GROUP_ADMIN.value in self.group_role_mapping.values():
            return Menu2Member.Roles.GROUP_ADMIN.value
        # 组员
        if self.group_role_mapping.values():
            return Menu2Member.Roles.ORDINARY.value

    def get_relation_group_set(self) -> list:
        """
        所在分组以及所有下级分组
        """
        relation_group_set = list()
        located_group_queryset = self.request.user.netflow_group_set.all()  # 当前用户所在的组
        for group in located_group_queryset:
            # 获取所有上级分组
            for parent_group in self.get_parent_groups(group):
                if parent_group not in relation_group_set:
                    relation_group_set.append(parent_group)
            # 获取所有下级分组
            for child_group in self.get_all_children_groups(group):
                if child_group not in relation_group_set:
                    relation_group_set.append(child_group)

        return relation_group_set

    def get_parent_groups(self, group: MenuModel) -> list:
        result = []
        while True:
            father = group.father
            if father:
                result.insert(0, father)
                group = father
            else:
                break
        return result

    def _get_group_role_mapping(self) -> dict[str:str]:
        """
        用户所在的组和下级分组和相应的角色
        {
            'group1':'role1',
            'group2':'role1',
            'group3':'role2',
        }
        """
        group_role_relation_mapping = dict()

        located_group_queryset = self.request.user.netflow_group_set.all()  # 当前用户所在的组
        for group in located_group_queryset.filter(menu2member__role=Menu2Member.Roles.ORDINARY.value):  # 组员
            for child_group in self.get_all_children_groups(group):
                group_role_relation_mapping[child_group.id] = Menu2Member.Roles.ORDINARY.value
        for group in located_group_queryset.filter(menu2member__role=Menu2Member.Roles.GROUP_ADMIN.value):  # 组管理员
            for child_group in self.get_all_children_groups(group):
                group_role_relation_mapping[child_group.id] = Menu2Member.Roles.GROUP_ADMIN.value
        return group_role_relation_mapping

    def get_all_children_groups(self, node: MenuModel) -> list:
        """
        获取当前分组和所有下级分组
        """
        if not node.sub_categories.all():
            return [node]
        else:
            return [node] + [child for child in node.sub_categories.all() for child in
                             self.get_all_children_groups(child)]

    def get_child_nodes(self, node_id):
        result = [node_id]
        for node in self.relation:  # 遍历所有节点
            if node['father_id'] != node_id:
                continue
            result.extend(self.get_child_nodes(node.get('id')))
        return result


class CustomPermission(BasePermission):
    """
    需要登陆
    """

    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        return True


class MenuListCustomPermission(BasePermission):
    """
    需要登陆
        超级管理员：读写权限
        其他用户：读权限
    """

    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        perm = PermissionManager(request)
        if perm.is_global_super_admin():  # 全局超级管理员 读写权限
            return True
        meta = request.META
        request_method = meta.get('REQUEST_METHOD')
        if request_method in SAFE_METHODS:  # 已登陆用户 读权限
            # 只返回当前用户有权限的分组列表
            return True


class MenuDetailCustomPermission(BasePermission):
    """
    需要登陆
    运维管理员  可读
    超级管理员 可读写
    """

    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        perm = PermissionManager(request)
        if perm.is_global_super_admin():  # 全局超级管理员 读写权限
            return True
        meta = request.META
        request_method = meta.get('REQUEST_METHOD')
        if request_method in SAFE_METHODS and perm.is_global_super_admin_or_ops_admin():  # 全局超级管理员 运维管理员 读权限
            return True


class Menu2ChartListCustomPermission(BasePermission):
    """
    需要登陆
    GET请求：
        全局超级管理员
        全局运维管理员
        组内成员
    POST请求：
        全局超级管理员
    """

    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        perm = PermissionManager(request)
        if perm.is_global_super_admin():  # 全局超级管理员 读写权限
            return True
        meta = request.META
        request_method = meta.get('REQUEST_METHOD')
        if request_method in SAFE_METHODS:  # 所有登录用户可读，仅返回有权限的元素集合
            return True


class Menu2ChartDetailCustomPermission(MenuDetailCustomPermission):
    """
      需要登陆
      运维管理员  可读
      超级管理员 可读写
      """
    pass


class Menu2MemberListCustomPermission(BasePermission):
    """
    1.查询组成员列表
    2.添加组成员
        需要登陆
        GET请求：
            全局超级管理员
            全局运维管理员
            组管理员
        POST请求：
            全局超级管理员
            组管理员
    """

    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        perm = PermissionManager(request)
        if perm.is_global_super_admin():  # 超级管理员  读写权限
            return True

        meta = request.META
        request_method = meta.get('REQUEST_METHOD')
        if request_method in SAFE_METHODS:
            if perm.is_global_ops_admin():  # 运维管理员 读权限
                return True

            menu_id = request.query_params.get("menu") or ''
            if menu_id and perm.has_group_admin_permission(menu_id):  # 组管理员 读权限
                return True
        if request_method == "POST":  # 添加组内成员
            menu_id = request.data.get('menu') or ''
            if menu_id and perm.has_group_admin_permission(menu_id):  # 组管理员 写权限
                return True


class Menu2MemberDetailCustomPermission(BasePermission):
    """
        1.查询指定组成员信息
        2.修改指定组成员信息
        3.删除指定组成员信息
    """

    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        perm = PermissionManager(request)
        if perm.is_global_super_admin():  # 超级管理员  读写权限
            return True
        meta = request.META
        request_method = meta.get('REQUEST_METHOD')
        if request_method in SAFE_METHODS and perm.is_global_ops_admin():  # 运维管理员 读权限
            return True

        if request_method in ["GET", "PUT", "DELETE"]:  # 当前组组管理员 或上级组管理员 读写权限
            menu_id = view.kwargs.get("pk")
            menu2member = Menu2Member.objects.filter(id=menu_id).first()
            if menu2member and menu2member.menu and perm.has_group_admin_permission(menu2member.menu.id):
                return True


class GlobalAdministratorCustomPermission(BasePermission):
    """
    全局超级管理员  可读可写
    运维管理员   可读
    """

    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        perm = PermissionManager(request)
        if perm.is_global_super_admin():  # 超级管理员  读写权限
            return True
        meta = request.META
        request_method = meta.get('REQUEST_METHOD')
        if request_method in SAFE_METHODS and perm.is_global_ops_admin():  # 运维管理员
            return True


class PortListCustomPermission(BasePermission):
    """
    全局超级管理员 可读
    """

    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        perm = PermissionManager(request)
        if perm.is_global_super_admin():  # 超级管理员  读写权限
            return True


class TrafficCustomPermission(BasePermission):
    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        perm = PermissionManager(request)
        if perm.is_global_super_admin_or_ops_admin():  # 全局管理员  读权限
            return True
        chart = request.data.get("chart") or ''
        element = Menu2Chart.objects.filter(id=chart).first()
        if element and element.menu and perm.has_group_permission(element.menu.id):
            return True
