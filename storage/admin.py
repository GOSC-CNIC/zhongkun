from django.contrib import admin

from . import models


@admin.register(models.ObjectsService)
class ObjectsServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'service_type', 'endpoint_url', 'add_time', 'status')


@admin.register(models.Bucket)
class BucketAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'service', 'access_perm', 'creation_time', 'lock', 'user')
    list_select_related = ('service', 'user')


@admin.register(models.BucketArchive)
class BucketArchiveAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'service', 'access_perm', 'creation_time', 'delete_time', 'lock', 'user')
    list_select_related = ('service', 'user')


@admin.register(models.StorageQuota)
class StorageQuotaAdmin(admin.ModelAdmin):
    list_display = ('id', 'service', 'count_total', 'count_used', 'size_gb_total',
                    'size_gb_used', 'creation_time', 'expiration_time', 'deleted', 'user')
    list_select_related = ('service', 'user')
