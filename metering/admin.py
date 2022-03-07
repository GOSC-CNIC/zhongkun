from django.contrib import admin

from .models import MeteringServer


@admin.register(MeteringServer)
class MeteringServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'cpu_hours', 'ram_hours', 'disk_hours', 'public_ip_hours',
                    'snapshot_hours', 'upstream', 'downstream' , 'pay_type', 'service',
                    'server_id', 'creation_time', 'owner_type', 'user_id', 'vo_id')
    list_display_links = ('id',)
    list_filter = ('owner_type',)
    search_fields = ('server_id',)
    list_select_related = ('service',)