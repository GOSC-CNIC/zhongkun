from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import Menu2Chart
from apps.app_netflow.models import Menu2Member
from apps.app_netflow.models import GlobalAdminModel
from apps.app_global.configs_manager import IPAccessWhiteListManager
from utils.iprestrict import IPRestrictor


class NetFlowAPIIPRestrictor(IPRestrictor):
    """
    流量模块 IP 白名单
    """

    def load_ip_rules(self):
        return IPAccessWhiteListManager.get_module_ip_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.NETFLOW.value)

    @staticmethod
    def clear_cache():
        IPAccessWhiteListManager.clear_cache()

    @staticmethod
    def add_ip_rule(ip_value: str):
        return IPAccessWhiteListManager.add_whitelist_obj(
            module_name=IPAccessWhiteListManager.ModuleName.NETFLOW.value, ip_value=ip_value)


class PermissionManager(object):
    def __init__(self, request):
        self.request = request
        self.user = self.request.user
        self.global_role = GlobalAdminModel.objects.filter(member=self.user).values_list('role', flat=True).first()
        self.relation_mapping = {_.get('id'): _.get('father_id') for _ in MenuModel.objects.values('id', 'father_id')}

    def is_global_ops_admin(self):
        """
        运维管理员
        """
        return self.global_role == GlobalAdminModel.Roles.ADMIN.value

    def is_global_super_admin(self):
        """
        超级管理员
        """
        return self.global_role == GlobalAdminModel.Roles.SUPER_ADMIN.value

    def is_global_admin(self):
        """
        全局管理员
            超级管理员
            运维管理员
        """
        return self.is_global_super_admin() or self.is_global_ops_admin()

    def user_group_list(self, is_admin=False):
        queryset = self.user.netflow_group_set.all()
        if is_admin:
            queryset = queryset.filter(menu2member__role=Menu2Member.Roles.GROUP_ADMIN.value)
        return queryset.values('id', 'name', 'father_id', 'level', 'sort_weight', 'remark', 'menu2member__role')

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

    def has_group_admin_permission(self, target_id: str):
        """
        具有当前组的访问权限
        """
        for group in self.user_group_list(is_admin=True):
            if self.is_parent_or_self(group.get('id'), target_id):
                return True

    def has_group_permission(self, target_id: str):
        """
        具有当前组的访问权限
        """
        groups = self.user_group_list()
        for group in groups:
            if self.is_parent_or_self(group.get('id'), target_id):
                return True

    def get_group_list(self, father, node_list):
        result = []
        for item in node_list:
            if item['father_id'] != father:  # 当前节点不是子节点
                continue
            if self.is_global_super_admin():  # TODO: 运维管理员角色查询速度优化
                item['admin'] = True
            elif self.has_group_admin_permission(item["id"]):
                item['admin'] = True
            else:
                item['admin'] = False
            if item['level'] < 2:
                item['sub_categories'] = self.get_group_list(item['id'], node_list)
            else:
                item['sub_categories'] = []
            result.append(item)
        return result

    def get_user_role(self):
        """
        当前用户的角色
        """
        if self.is_global_super_admin():
            return GlobalAdminModel.Roles.SUPER_ADMIN.value
        if self.is_global_ops_admin():
            return GlobalAdminModel.Roles.ADMIN.value
        if self.user_group_list(is_admin=True):
            return Menu2Member.Roles.GROUP_ADMIN.value
        else:
            return Menu2Member.Roles.ORDINARY.value


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
        perm = PermissionManager(request)
        if not user.is_authenticated:  # 需要登陆
            return False
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
        perm = PermissionManager(request)
        if not user.is_authenticated:  # 需要登陆
            return False
        if perm.is_global_super_admin():  # 全局超级管理员 读写权限
            return True
        meta = request.META
        request_method = meta.get('REQUEST_METHOD')
        if request_method in SAFE_METHODS and perm.is_global_admin():  # 全局超级管理员 运维管理员 读权限
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
        perm = PermissionManager(request)
        if not user.is_authenticated:  # 需要登陆
            return False
        if perm.is_global_super_admin():  # 全局超级管理员 读写权限
            return True
        meta = request.META
        request_method = meta.get('REQUEST_METHOD')
        if request_method in SAFE_METHODS:
            if perm.is_global_ops_admin():  # 运维管理员 读权限
                return True
            group_id = request.query_params.get("menu") or ''
            if group_id and perm.has_group_permission(group_id):  # 组员或组管理员 读权限
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
        perm = PermissionManager(request)
        if not user.is_authenticated:  # 需要登陆
            return False
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
        perm = PermissionManager(request)
        if not user.is_authenticated:  # 需要登陆
            return False
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
        perm = PermissionManager(request)
        if not user.is_authenticated:  # 需要登陆
            return False
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
        perm = PermissionManager(request)
        if not user.is_authenticated:  # 需要登陆
            return False
        if perm.is_global_super_admin():  # 超级管理员  读写权限
            return True


class TrafficCustomPermission(BasePermission):
    def has_permission(self, request, view):
        NetFlowAPIIPRestrictor().check_restricted(request=request)
        user = request.user
        perm = PermissionManager(request)
        if not user.is_authenticated:  # 需要登陆
            return False
        if perm.is_global_admin():  # 全局管理员  读权限
            return True
        chart = request.data.get("chart") or ''
        element = Menu2Chart.objects.filter(id=chart).first()
        if element and element.menu and perm.has_group_permission(element.menu.id):
            return True
