from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import BasePermission
from apps.app_netflow.models import MenuModel
from django.forms.models import model_to_dict


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


class SubCategoryPermission(BasePermission):
    """
    二级菜单栏权限
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:  # 需要登陆
            return False
        permissions = UserPermissions(request=request)
        return permissions.has_menu_permission()
