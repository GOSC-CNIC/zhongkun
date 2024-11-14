from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms.widgets import PasswordInput


class KunYuanServiceForm(forms.ModelForm):
    change_password = forms.CharField(
        label=_('更改用户密码输入'), required=False, min_length=6, max_length=32,
        help_text=_('如果要更改服务认证用户密码，请在此输入新密码, 不修改请保持为空'))

    class Meta:
        widgets = {
            'remarks': forms.Textarea(attrs={'cols': 80, 'rows': 6}),
            "password": PasswordInput(
                attrs={'placeholder': '********', 'autocomplete': 'off', 'data-toggle': 'password'}),
        }

    def save(self, commit=True):
        change_password = self.cleaned_data.get('change_password')      # 如果输入新密码则更改
        if change_password:
            self.instance.set_password(change_password)

        return super().save(commit=commit)
