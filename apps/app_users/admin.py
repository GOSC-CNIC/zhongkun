from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.html import format_html
from django.utils import timezone as dj_timezone
from django.urls import reverse

from core.taskqueue import submit_task
from utils.model import BaseModelAdmin
from utils.report_file import CSVFileInMemory, wrap_csv_file_response
from .models import UserProfile, Email
from .forms import UserModelForm


@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    form = UserModelForm

    list_display = ('id', 'username', 'fullname', 'company', 'telephone', 'is_active', 'is_superuser',
                    'is_staff', 'is_fed_admin', 'date_joined', 'last_active', 'organization')
    list_display_links = ('id', 'username')
    list_filter = ('is_superuser', 'is_staff', 'is_fed_admin', 'is_active')
    search_fields = ('username', 'company', 'first_name', 'last_name')  # 搜索字段
    list_select_related = ('organization',)
    raw_id_fields = ('organization',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('个人信息'), {'fields': ('first_name', 'last_name', 'email', 'company', 'telephone', 'organization')}),
        (_('权限信息'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_fed_admin', 'groups', 'user_permissions')}),
        (_('重要日期'), {'fields': ('date_joined',)}),
    )
    ordering = ['date_joined']
    actions = ('export_select_users',)

    class Media:
        css = {
            'all': ['yunkun/admin/common.css']
        }

    @admin.display(description=_('姓名'))
    def fullname(self, obj):
        return obj.get_full_name()

    @admin.action(description=_('导出选中的用户'))
    def export_select_users(self, request, queryset):
        t = dj_timezone.now()
        filename = f"users-{t.year:04}{t.month:02}{t.day:02}{t.hour:02}{t.minute:02}{t.second:02}"
        csv_file = CSVFileInMemory(filename=filename)
        csv_file.writerow([
            gettext('用户名'), gettext('姓名'), gettext('邮箱'), gettext('电话'),
            gettext('单位/公司'), gettext('加入日期'), gettext('最后活跃日期')
        ])

        for user in queryset:
            row_items = [
                user.username, user.get_full_name(), user.email,
                user.telephone, user.company, user.date_joined.isoformat(),
                user.last_active.isoformat(),
            ]
            csv_file.writerow(row_items)

        filename = csv_file.filename
        data = csv_file.to_bytes()
        csv_file.close()
        return wrap_csv_file_response(filename=filename, data=data)


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
        disp = gettext('预览')
        return format_html(f'<a target="view_frame" href="{preview_url}">{disp}</a>')

    @admin.action(description=_('重试发送失败邮件'))
    def resend_failed_email(self, request, queryset):
        for email in queryset:
            if email.is_feint:  # 假动作，不真实发送
                continue

            if email.status == email.Status.SUCCESS.value:
                continue

            submit_task(Email.do_send_email, kwargs={'email': email, 'save_db': True})
