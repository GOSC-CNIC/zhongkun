from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from core.taskqueue import submit_task
from utils.model import BaseModelAdmin
from .models import UserProfile, Email
from .forms import UserModelForm


@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    form = UserModelForm

    list_display = ('id', 'username', 'fullname', 'company', 'telephone', 'is_active', 'is_superuser',
                    'is_staff', 'is_fed_admin', 'date_joined')
    list_display_links = ('id', 'username')
    list_filter = ('is_superuser', 'is_staff', 'is_fed_admin')
    search_fields = ('username', 'company', 'first_name', 'last_name')  # 搜索字段

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('个人信息'), {'fields': ('first_name', 'last_name', 'email', 'company', 'telephone')}),
        (_('权限信息'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_fed_admin', 'groups', 'user_permissions')}),
        (_('重要日期'), {'fields': ('date_joined',)}),
    )
    ordering = ['date_joined']

    class Media:
        css = {
            'all': ['yunkun/admin/common.css']
        }

    def fullname(self, obj):
        return obj.get_full_name()

    fullname.short_description = _('姓名')


@admin.register(Email)
class EmailAdmin(BaseModelAdmin):
    list_display = ('show_preview_url', 'id', 'subject', 'tag', 'receiver', 'sender',
                    'status', 'success_time', 'send_time', 'is_html', 'remote_ip', 'status_desc')
    list_display_links = ('id', 'subject')
    list_filter = ('tag', 'status', 'is_feint')
    search_fields = ('subject', 'receiver', 'remote_ip')
    actions = ('resend_failed_email',)

    @admin.display(description=_('预览'))
    def show_preview_url(self, obj):
        preview_url = reverse('users:email-detail', kwargs={'email_id': obj.id})
        return format_html(f'<a target="view_frame" href="{preview_url}">预览</a>')

    @admin.action(description=_('重试发送失败邮件'))
    def resend_failed_email(self, request, queryset):
        for email in queryset:
            if email.is_feint:  # 假动作，不真实发送
                continue

            if email.status == email.Status.SUCCESS.value:
                continue

            submit_task(Email.do_send_email(email=email, save_db=True))
