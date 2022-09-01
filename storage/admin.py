from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from . import models
from . import forms


@admin.register(models.ObjectsService)
class ObjectsServiceAdmin(admin.ModelAdmin):
    form = forms.ObjectsServiceForm

    list_display = ('id', 'name', 'name_en', 'data_center', 'service_type', 'endpoint_url', 'add_time', 'status',
                    'username', 'raw_password', 'provide_ftp', 'pay_app_service_id')

    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = ['data_center', 'service_type']
    list_select_related = ('data_center',)

    filter_horizontal = ('users',)
    readonly_fields = ('password', )
    fieldsets = (
        (_('说明、备注'), {'fields': ('remarks',)}),
        (_('服务配置信息'), {
            'fields': ('data_center', 'name', 'name_en', 'service_type', 'status', 'endpoint_url',
                       'api_version', 'username', 'password', 'change_password')
        }),
        (_('FTP配置信息'), {
            'fields': ('provide_ftp', 'ftp_domains')
        }),
        (_('支付结算信息'), {'fields': ('pay_app_service_id',)}),
        (_('其他配置信息'), {'fields': ('extra', 'logo_url', 'longitude', 'latitude')}),
        (_('服务管理员'), {'fields': ('users',)}),
        (_('联系人信息'), {
            'fields': ('contact_person', 'contact_email', 'contact_telephone', 'contact_fixed_phone', 'contact_address')
        }),
    )


@admin.register(models.Bucket)
class BucketAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'bucket_id', 'service', 'creation_time', 'user')
    list_select_related = ('service', 'user')
    raw_id_fields = ('user',)


@admin.register(models.BucketArchive)
class BucketArchiveAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'service', 'creation_time', 'user', 'delete_time', 'archiver')
    list_select_related = ('service', 'user')
    raw_id_fields = ('user',)
