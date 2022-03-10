from django.contrib import admin

from .models import MeteringServer, MeteringDisk, MeteringObjectStorage


@admin.register(MeteringServer)
class MeteringServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'cpu_hours', 'ram_hours', 'disk_hours', 'public_ip_hours',
                    'snapshot_hours', 'upstream', 'downstream', 'pay_type', 'service',
                    'server_id', 'creation_time', 'owner_type', 'user_id', 'vo_id')
    list_display_links = ('id',)
    list_filter = ('owner_type',)
    search_fields = ('server_id', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(MeteringDisk)
class MeteringDiskAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'size_hours', 'snapshot_hours', 'pay_type', 'service',
                    'disk_id', 'creation_time', 'owner_type', 'user_id', 'vo_id')
    list_display_links = ('id',)
    list_filter = ('owner_type',)
    search_fields = ('server_id', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(MeteringObjectStorage)
class MeteringObjectStorageAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'storage', 'downstream', 'replication', 'get_request',
                    'put_request', 'pay_type', 'service', 'bucket_name', 'bucket_id',
                    'creation_time', 'user_id')
    list_display_links = ('id',)
    list_filter = ('user_id',)
    search_fields = ('bucket_name', 'user_id')
    list_select_related = ('service',)
