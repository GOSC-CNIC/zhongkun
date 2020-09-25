from django.contrib import admin

from .models import Server, Flavor


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'name', 'instance_id', 'flavor_id', 'vcpus', 'ram', 'ipv4', 'image_id', 'image',
                    'creation_time', 'user', 'remarks')
    search_fields = ['name', 'image', 'ipv4', 'remarks']
    list_filter = ['service']
    raw_id_fields = ('user',)
    list_select_related = ('user',)


@admin.register(Flavor)
class FlavorAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpus', 'ram', 'enable', 'creation_time')
