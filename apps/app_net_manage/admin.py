from django.contrib import admin

from utils.model import BaseModelAdmin
from apps.app_net_manage.models import OrgVirtualObject, ContactPerson, NetManageUserRole


@admin.register(OrgVirtualObject)
class OrgVirtualObjectAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'organization', 'creation_time', 'remark')
    list_select_related = ('organization',)
    raw_id_fields = ('organization',)
    search_fields = ('name', 'organization__name', 'remark')
    filter_horizontal = ('contacts',)
    readonly_fields = ('creation_time',)


@admin.register(ContactPerson)
class ContactPersonAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'telephone', 'email', 'address', 'creation_time', 'remarks')

    search_fields = ('name', 'telephone', 'email', 'address', 'remarks')
    readonly_fields = ('creation_time', 'update_time')


@admin.register(NetManageUserRole)
class NetManageUserRoleAdmin(BaseModelAdmin):
    list_display = ('id', 'user', 'role', 'creation_time', 'update_time')
    list_select_related = ('user',)
    raw_id_fields = ('user',)
    search_fields = ('user_username',)
