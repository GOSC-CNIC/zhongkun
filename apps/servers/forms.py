from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms.widgets import PasswordInput
from django.forms.utils import ErrorList
from django_json_widget.widgets import JSONEditorWidget


class JSONEditorAllowEmptyWidget(JSONEditorWidget):
    def format_value(self, value):
        if not value:
            value = '{}'
        return super(JSONEditorAllowEmptyWidget, self).format_value(value)


class VmsProviderForm(forms.ModelForm):
    change_password = forms.CharField(label=_('更改用户密码输入'), required=False, min_length=6, max_length=32,
                                      help_text=_('如果要更改服务认证用户密码，请在此输入新密码, 不修改请保持为空'))
    change_vpn_password = forms.CharField(label=_('更改VPN用户密码输入'), required=False, min_length=6, max_length=32,
                                          help_text=_('如果要更改服务VPN认证用户密码，请在此输入新密码, 不修改请保持为空'))
    create_monitor_task = forms.BooleanField(
        label=_('创建服务单元站点监控任务'), required=False,
        help_text=_('选中后会自动为服务单元创建或更新站点监控任务，当取消选中时会尝试删除对应监控任务'))

    class Meta:
        widgets = {
            'extra': JSONEditorAllowEmptyWidget(),
            'remarks': forms.Textarea(attrs={'cols': 80, 'rows': 6}),
            "password": PasswordInput(
                attrs={'placeholder': '********', 'autocomplete': 'off', 'data-toggle': 'password'}),
        }

    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=ErrorList,
        label_suffix=None,
        empty_permitted=False,
        instance=None,
        use_required_attribute=None,
        renderer=None,
    ):
        if instance and instance.monitor_task_id:
            if initial:
                initial['create_monitor_task'] = True
            else:
                initial = {'create_monitor_task': True}

        super().__init__(
            data=data, files=files, auto_id=auto_id, prefix=prefix, initial=initial,
            error_class=error_class, label_suffix=label_suffix, empty_permitted=empty_permitted,
            instance=instance, use_required_attribute=use_required_attribute, renderer=renderer
        )

    def save(self, commit=True):
        change_password = self.cleaned_data.get('change_password')      # 如果输入新密码则更改
        change_vpn_password = self.cleaned_data.get('change_vpn_password')  # 如果输入新密码则更改
        if change_password:
            self.instance.set_password(change_password)

        if change_vpn_password:
            self.instance.set_vpn_password(change_vpn_password)

        return super().save(commit=commit)
