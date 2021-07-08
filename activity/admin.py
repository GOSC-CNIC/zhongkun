from django.contrib import admin

from .models import QuotaActivity, QuotaActivityGotRecord


@admin.register(QuotaActivity)
class QuotaActivityAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'start_time', 'end_time', 'count', 'got_count',
                    'times_per_user', 'creation_time', 'status', 'deleted', 'service', 'user')
    list_select_related = ('user', 'service')
    search_fields = ('name', 'name_en')
    list_filter = ('service', 'status', 'deleted')


@admin.register(QuotaActivityGotRecord)
class QuotaActivityGotRecordAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'quota_activity', 'user', 'got_time')
    list_select_related = ('user', 'quota_activity')
    search_fields = ('user__username', 'quota_activity__id')
