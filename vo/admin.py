from django.contrib import admin

from .models import VirtualOrganization, VoMember


@admin.register(VirtualOrganization)
class VoAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'creation_time', 'owner', 'company', 'is_deleted', 'description')
    search_fields = ['name', 'company', 'description']
    list_filter = ['creation_time', 'deleted']
    list_select_related = ('owner',)

    filter_horizontal = ('members',)

    @admin.display(description='删除')
    def is_deleted(self, obj):
        if obj.deleted:
            return 'yes'

        return 'no'


@admin.register(VoMember)
class VoMemberAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'user', 'vo', 'role', 'join_time', 'inviter', 'inviter_id')
    search_fields = ['user__username', 'vo__name', 'inviter']
    list_filter = ['join_time',]
    list_select_related = ('user', 'vo')
