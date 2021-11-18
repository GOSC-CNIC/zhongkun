from django.contrib import admin

from .models import MonitorJobCeph, MonitorProvider, MonitorJobServer, MonitorJobVideoMeeting


@admin.register(MonitorProvider)
class MonitorProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'endpoint_url', 'username', 'password', 'creation')
    list_display_links = ('name', )
    readonly_fields = ('password', )


@admin.register(MonitorJobCeph)
class MonitorJobCephAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'job_tag', 'provider', 'service', 'creation')
    list_display_links = ('name', )
    list_select_related = ('provider', 'service')


@admin.register(MonitorJobServer)
class MonitorJobServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'job_tag', 'provider', 'service', 'creation')
    list_display_links = ('name', )
    list_select_related = ('provider', 'service')


@admin.register(MonitorJobVideoMeeting)
class MonitorJobVideoMeetingAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'job_tag', 'ips', 'longitude', 'latitude', 'provider', 'creation')
    list_display_links = ('name', )
    list_select_related = ('provider',)
