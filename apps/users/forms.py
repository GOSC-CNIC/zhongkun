import json

from django import forms
from django.utils.translation import gettext_lazy, gettext as _
from django_json_widget.widgets import JSONEditorWidget
from django.contrib.auth.forms import UserChangeForm

from .models import default_role


class PasswordForm(forms.Form):
    new_password = forms.CharField(label=gettext_lazy('新密码'),
                                   min_length=8,
                                   max_length=20,
                                   widget=forms.PasswordInput(attrs={
                                       'class': 'form-control',
                                       'placeholder': gettext_lazy('请输入一个8-20位的新密码')
                                   }))
    confirm_new_password = forms.CharField(label=gettext_lazy('确认新密码'),
                                           min_length=8,
                                           max_length=20,
                                           widget=forms.PasswordInput(attrs={
                                               'class': 'form-control',
                                               'placeholder': gettext_lazy('请再次输入新密码')
                                           }))

    def clean(self):
        """
        验证表单提交的数据
        """
        new_password = self.cleaned_data.get('new_password')
        confirm_new_password = self.cleaned_data.get('confirm_new_password')
        if new_password != confirm_new_password or not new_password:
            raise forms.ValidationError(_('密码输入不一致'))
        return self.cleaned_data


class PasswordChangeForm(PasswordForm):
    """
    用户密码修改表单
    """
    old_password = forms.CharField(label=gettext_lazy('原密码'),
                                   min_length=8,
                                   max_length=20,
                                   widget=forms.PasswordInput(attrs={
                                                'class': 'form-control',
                                                'placeholder': gettext_lazy('请输入原密码')
                                   }))
    # new_password = forms.CharField(label=gettext_lazy('新密码'),
    #                                min_length=8,
    #                                max_length=20,
    #                                widget=forms.PasswordInput(attrs={
    #                                             'class': 'form-control',
    #                                             'placeholder': gettext_lazy('请输入一个8-20位的新密码')
    #                                }))
    # confirm_new_password = forms.CharField(label=gettext_lazy('确认新密码'),
    #                                        min_length=8,
    #                                        max_length=20,
    #                                        widget=forms.PasswordInput(attrs={
    #                                             'class': 'form-control',
    #                                             'placeholder': gettext_lazy('请再次输入新密码')
    #                                        }))

    def __init__(self, *args, **kwargs):
        if 'user' in kwargs:
            self.user = kwargs.pop('user')
        super(PasswordChangeForm, self).__init__(*args, **kwargs)

    # def clean(self):
    #     """
    #     验证表单提交的数据
    #     """
    #     new_password = self.cleaned_data.get('new_password')
    #     confirm_new_password = self.cleaned_data.get('confirm_new_password')
    #     if new_password != confirm_new_password or not new_password:
    #         raise forms.ValidationError(_('密码输入不一致'))
    #     return self.cleaned_data

    def clean_old_password(self):
        """
        验证原密码
        """
        old_password = self.cleaned_data.get('old_password')

        # 如果当前用户为第三方登录，且还未设置本地密码，跳过原密码检验
        if self.user.third_app != self.user.ThirdApp.LOCAL_USER.value and not self.user.password:
            return old_password

        if not self.user.check_password(old_password):
            raise forms.ValidationError(_('原密码有误'))
        return old_password


class RoleJSONEditorWidget(JSONEditorWidget):
    def format_value(self, value):
        if not value:
            value = json.dumps(default_role())
        return super(RoleJSONEditorWidget, self).format_value(value)


class UserModelForm(UserChangeForm):
    class Meta:
        widgets = {
            'role': RoleJSONEditorWidget(),
        }
