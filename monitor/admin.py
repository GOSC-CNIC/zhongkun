from django.contrib import admin
from django.db import transaction
from django.utils import timezone
from django.forms import ModelForm
from django.core.exceptions import ValidationError

from utils.model import NoDeleteSelectModelAdmin
from .models import (
    MonitorJobCeph, MonitorProvider, MonitorJobServer, MonitorJobVideoMeeting,
    MonitorWebsite, MonitorWebsiteTask, MonitorWebsiteVersion,
    get_str_hash, WebsiteDetectionPoint, MonitorJobTiDB
)
from .managers import MonitorWebsiteManager


@admin.register(MonitorProvider)
class MonitorProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'endpoint_url', 'receive_url', 'bucket_name',
                    'bucket_service_name', 'bucket_service_url', 'username', 'password', 'creation')
    list_display_links = ('name', )
    readonly_fields = ('password', )


@admin.register(MonitorJobCeph)
class MonitorJobCephAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'organization', 'sort_weight', 'job_tag', 'provider',
                    'service', 'prometheus', 'creation')
    list_display_links = ('name', )
    list_select_related = ('provider', 'organization')
    list_editable = ('sort_weight',)
    list_filter = ('organization',)
    filter_horizontal = ('users',)


@admin.register(MonitorJobServer)
class MonitorJobServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'organization', 'sort_weight', 'job_tag', 'provider',
                    'service', 'prometheus', 'creation')
    list_display_links = ('name', )
    list_select_related = ('provider', 'organization')
    list_editable = ('sort_weight',)
    list_filter = ('organization',)
    filter_horizontal = ('users',)


@admin.register(MonitorJobVideoMeeting)
class MonitorJobVideoMeetingAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'job_tag', 'ips', 'longitude', 'latitude', 'provider', 'prometheus', 'creation')
    list_display_links = ('name', )
    list_select_related = ('provider',)


class MonitorWebsiteForm(ModelForm):
    def clean(self):
        data = super().clean()
        ws_url = data['url']
        user = data['user']
        if not user:
            self.add_error('user', ValidationError('必须选择一个用户。'))
        else:
            url_hash = get_str_hash(ws_url)
            _website = MonitorWebsite.objects.filter(user_id=user.id, url_hash=url_hash).first()
            if _website is not None:
                self.add_error('url', ValidationError('指定用户已存在相同的网址。'))

        return data


@admin.register(MonitorWebsite)
class MonitorWebsiteAdmin(NoDeleteSelectModelAdmin):
    form = MonitorWebsiteForm

    list_display = ('id', 'name', 'url', 'is_attention', 'url_hash', 'creation', 'modification', 'user')
    list_display_links = ('id', 'name')
    list_select_related = ('user',)
    raw_id_fields = ('user',)
    search_fields = ('name', 'url', 'user__username')
    readonly_fields = ('url_hash',)

    def save_model(self, request, obj, form, change):
        if change:
            old_website = MonitorWebsite.objects.filter(id=obj.id).first()
            new_url = obj.url
            obj.url = old_website.url
            MonitorWebsiteManager.do_change_website_task(user_website=obj, new_url=new_url)
        else:
            MonitorWebsiteManager.do_add_website_task(user_website=obj)

    def delete_model(self, request, obj):
        MonitorWebsiteManager.do_delete_website_task(user_website=obj)


@admin.register(MonitorWebsiteTask)
class MonitorWebsiteTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'url_hash', 'creation')
    list_display_links = ('id', )
    search_fields = ('url',)
    readonly_fields = ('url_hash',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MonitorWebsiteVersion)
class MonitorWebsiteVersionProviderAdmin(NoDeleteSelectModelAdmin):
    list_display = ('id', 'version', 'creation', 'modification')
    list_display_links = ('id', )
    readonly_fields = ('id', 'creation', 'modification')

    def save_model(self, request, obj: MonitorWebsiteVersion, form, change):
        # 确保版本编号无误，防止并发
        with transaction.atomic():
            vers = MonitorWebsiteVersion.get_instance(select_for_update=True)
            # 后台填写的版本号大于当前版本号时，+1，防止后台填入一个很大的数值
            if vers.version < obj.version:
                vers.version += 1

            vers.modification = timezone.now()
            vers.save(force_update=True)


@admin.register(WebsiteDetectionPoint)
class WebsiteDetectionPointAdmin(NoDeleteSelectModelAdmin):
    list_display = ('id', 'name', 'name_en', 'provider', 'enable', 'creation', 'modification')
    list_display_links = ('id', )
    list_select_related = ('provider',)
    list_filter = ('enable',)


@admin.register(MonitorJobTiDB)
class MonitorJobTiDBAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'organization', 'sort_weight', 'version', 'job_tag',
                    'provider', 'service', 'prometheus', 'creation')
    list_display_links = ('name', )
    list_select_related = ('provider', 'organization')
    list_editable = ('sort_weight',)
    list_filter = ('organization',)
    filter_horizontal = ('users',)
