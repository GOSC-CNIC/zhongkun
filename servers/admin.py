from django.contrib import admin

from .models import Server, ServiceConfig


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'name', 'instance_id', 'flavor_id', 'vcpus', 'ram', 'ipv4', 'image_id', 'image',
                    'creation_time', 'deleted', 'user', 'remarks')
    search_fields = ['name', 'image', 'ipv4', 'remarks']
    list_filter = ['service']
    raw_id_fields = ('user',)
    list_select_related = ('user',)


@admin.register(ServiceConfig)
class ServiceConfigAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'region_id', 'service_type', 'endpoint_url', 'username', 'password',
                    'add_time', 'active', 'remarks')
    search_fields = ['name', 'endpoint_url', 'remarks']
    list_filter = ['service_type']

