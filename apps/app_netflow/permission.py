from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import BasePermission
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import RoleModel
from django.forms.models import model_to_dict


class Permission(object):
    def __init__(self, request):
        self.request = request
        self.user = self.request.user

    def is_super_admin(self):
        """
        超级管理员
        """
        role = self.user.netflow_role_set.filter(role=RoleModel.Roles.SUPER_ADMIN.value).first()
        if role:
            return True

    def is_admin(self):
        """
        管理员
        """
        role = self.user.netflow_role_set.filter(role=RoleModel.Roles.ADMIN.value).first()
        if role:
            return True


def has_netflow_admin_permission(user):
    """
    超级管理员
    """
    role_set = user.netflow_role_set.all()
    for role in role_set:
        if role.role == RoleModel.Roles.SUPER_ADMIN.value:
            return True


class UserPermissions(object):
    def __init__(self, request):
        self.request = request
        self.user = self.request.user

    def user_accessible_chart_set(self):
        netflow_role = self.user.netflow_role_set.all()
        permission_mapping = set()
        for role in netflow_role:
            role_menus = role.menus.all()
            role_charts = role.charts.all()
            for menu in role_menus:
                for chart in menu.chart.all():
                    permission_mapping.add(chart)
            for chart in role_charts:
                permission_mapping.add(chart)
        return permission_mapping

    def user_accessible_menu_set(self):
        netflow_role = self.user.netflow_role_set.all()
        permission_set = set()
        for role in netflow_role:
            role_menus = role.menus.all()
            for menu in role_menus:
                permission_set.add(menu)
        return permission_set

    def has_menu_permission(self):
        accessible_menu_set = self.user_accessible_menu_set()
        for menu in accessible_menu_set:
            params = self.request.query_params
            request_menu = params.get('menu') or ''
            if request_menu == menu.id:
                return True


class MenuPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        if user.is_superuser:
            return True


class CustomPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        if user.is_superuser:
            return True
