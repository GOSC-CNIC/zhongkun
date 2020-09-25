from django.contrib import admin

from .models import ServiceConfig


@admin.register(ServiceConfig)
class ServiceConfigAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'region_id', 'service_type', 'endpoint_url', 'username', 'password',
                    'add_time', 'status', 'remarks')
    search_fields = ['name', 'endpoint_url', 'remarks']
    list_filter = ['service_type']






