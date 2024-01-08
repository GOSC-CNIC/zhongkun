from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import VirtualOrganization, VoMember


@admin.register(VirtualOrganization)
class VoAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'creation_time', 'owner', 'company', 'is_deleted', 'description')
    search_fields = ['name', 'company', 'description']
    list_filter = ['creation_time', 'deleted']
    list_select_related = ('owner',)
    raw_id_fields = ('owner',)

    filter_horizontal = ('members',)

    @admin.display(description=_('删除'))
    def is_deleted(self, obj):
        if obj.deleted:
            return 'yes'

        return 'no'

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VoMember)
class VoMemberAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'user', 'vo', 'role', 'join_time', 'inviter', 'inviter_id')
    search_fields = ['user__username', 'vo__name', 'inviter']
    list_filter = ['join_time',]
    list_select_related = ('user', 'vo')
    raw_id_fields = ('user',)
