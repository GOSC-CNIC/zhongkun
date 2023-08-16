import requests
import json
from urllib import parse

from django.shortcuts import render, redirect, resolve_url
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from django.contrib.auth.views import LoginView
from django.views import View
from django.utils import timezone

from .models import Email
from . import forms


User = get_user_model()     # 获取用户模型


def replace_query_params(url, params: dict):
    """
    替换或添加url中query参数的值
    :param url: url
    :param params: 键值对参数
    :return:
        new url; type str
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(force_str(url))
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    for key, val in params.items():
        query_dict[force_str(key)] = [force_str(val)]
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


class KJYLogin:
    @classmethod
    def as_view(cls):
        return cls().kjy_login_callback

    def kjy_login_callback(self, request, *args, **kwargs):
        """
        第三方科技云通行证登录回调视图
        """
        code = request.GET.get('code', None)
        if not code:
            return self.kjy_logout()

        token = self.get_kjy_auth_token(code=code)
        if not token:
            return self.kjy_logout()

        user = self.create_kjy_auth_user(request, token)
        if not user:
            return self.kjy_logout()

        # 标记当前为科技云通行证登录用户
        if user.third_app != user.ThirdApp.KJY_PASSPORT.value:
            user.third_app = user.ThirdApp.KJY_PASSPORT.value
            user.last_active = timezone.now()
            user.save(update_fields=['third_app', 'last_active'])

        login(request, user)        # 登录用户
        return redirect(to='/')

    def create_kjy_auth_user(self, request, token):
        """
        创建科技云通行证登录认证的用户

        :param request: 请求体
        :param token:  科技云通行证登录认证token
        :return:
            success: User()
            failed: None
        """
        user_info = self.get_user_info_from_token(token)
        if not user_info:
            return None

        is_active = user_info.get('cstnetIdStatus')
        email = user_info.get('cstnetId')
        truename = user_info.get('truename')

        if is_active != 'active':   # 未激活用户
            return None

        # 邮箱对应用户是否已存在
        try:
            user = User.objects.filter(username=email).first()
        except Exception as e:
            user = None

        if user:    # 已存在, 返回用户
            return user

        # 创建用户
        try:
            first_name, last_name = self.get_first_and_last_name(truename)
        except Exception:
            first_name, last_name = '', ''
        user = User(username=email, email=email, first_name=first_name, last_name=last_name)
        try:
            user.save()
        except Exception as e:
            return None

        return user

    @staticmethod
    def get_first_and_last_name(name: str):
        """
        粗略切分姓和名
        :param name: 姓名
        :return:
            (first_name, last_name)
        """
        if not name:
            return '', ''

        # 如果是英文名
        if name.replace(' ', '').encode('UTF-8').isalpha():
            names = name.rsplit(' ', maxsplit=1)
            if len(names) == 2:
                first_name, last_name = names
            else:
                first_name, last_name = name, ''
        elif len(name) == 4:
            first_name, last_name = name[2:], name[:2]
        else:
            first_name, last_name = name[1:], name[:1]

        # 姓和名长度最大为30
        if len(first_name) > 30:
            first_name = first_name[:31]

        if len(last_name) > 30:
            last_name = last_name[:31]

        return first_name, last_name

    @staticmethod
    def get_kjy_login_url():
        """
        获取 中国科技云通行证登录url
        :return:
            success: url
            failed: None
        """
        kjy_settings = settings.THIRD_PARTY_APP_AUTH.get('SCIENCE_CLOUD')
        kjy_security_settings = settings.THIRD_PARTY_APP_AUTH_SECURITY.get('SCIENCE_CLOUD')
        if not kjy_settings or not kjy_security_settings:
            return None

        client_id = kjy_security_settings.get('client_id')
        client_callback_url = kjy_settings.get('client_callback_url')
        login_url = kjy_settings.get('login_url')
        params = {
            'client_id': client_id,
            'redirect_uri': client_callback_url,
        }
        try:
            url = replace_query_params(url=login_url, params=params)
        except:
            return None

        return url

    @staticmethod
    def get_kjy_auth_token(code):
        """
        获取登录认证后的token

        :param code: 认证成功后回调url中的param参数code
        :return:
            success:
            {
                "access_token":  "SlAV32hkKG",
                "expires_in":  3600,
                “refresh_token:  ”ASAEDFIkie876”,
                ”userInfo”: {
                    “umtId”:  12,                     # 对应umt里面的id号
                    “truename”:  ”yourName”,        # 用户真实姓名
                    ”type”:  ”umtauth”,             # 账户所属范围umt、coremail、uc
                    ”securityEmail”: ” securityEmail”, # 密保邮箱
                    ”cstnetIdStatus”: ”cstnetIdStatus”, # 主账户激活状态，即邮箱验证状态， 可选值：active-已激活，temp-未激活。应用可根据此状态判断是否允许该用户登录
                    ”cstnetId”: ”yourEmail”,            # 用户主邮箱
                    “passwordType”:” password_umt”,     # 登录的密码类型
                    ”secondaryEmails”:[“youremail1”, “youremail2”] # 辅助邮箱
                }
            }

            failed: None
        """
        kjy_settings = settings.THIRD_PARTY_APP_AUTH.get('SCIENCE_CLOUD')
        kjy_security_settings = settings.THIRD_PARTY_APP_AUTH_SECURITY.get('SCIENCE_CLOUD')
        if not kjy_settings or not kjy_security_settings:
            return None

        client_id = kjy_security_settings.get('client_id')
        client_secret = kjy_security_settings.get('client_secret')
        client_callback_url = kjy_settings.get('client_callback_url')
        token_url = kjy_settings.get('token_url')
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': client_callback_url,
            'code': code,
            'grant_type': 'authorization_code'
        }

        try:
            r = requests.post(url=token_url, data=data)
            if r.status_code == 200:
                token = r.json()
            else:
                token = None
        except Exception as e:
            return None

        return token

    @staticmethod
    def get_user_info_from_token(token):
        """
        从token中获取用户信息

        :param token:
        :return:
            success: user_info ; type:dict
            failed: None
        """
        user_info = token.get('userInfo')
        if isinstance(user_info, str):
            try:
                user_info = json.loads(user_info)
            except:
                user_info = None

        return user_info

    @staticmethod
    def get_kjy_logout_url(redirect_uri=None):
        """
        科技云通行证登出url

        :param redirect_uri: 登出后重定向的url
        :return:
            success: url
            failed: None
        """
        kjy_settings = settings.THIRD_PARTY_APP_AUTH.get('SCIENCE_CLOUD')
        if not kjy_settings:
            return None

        logout_url = kjy_settings.get('logout_url')
        if not redirect_uri:
            redirect_uri = kjy_settings.get('client_home_url')

        try:
            url = replace_query_params(url=logout_url, params={'WebServerURL': redirect_uri})
        except:
            return None

        return url

    @classmethod
    def kjy_logout(cls, next_to=None):
        """
        登出科技云账户

        :param next_to: 登出后重定向的url
        :return:
        """
        url = cls.get_kjy_logout_url(next_to)
        return redirect(to=url)


class LocalSignInView(LoginView):
    redirect_authenticated_user = True

    def form_valid(self, form):
        r = super().form_valid(form)
        user = form.get_user()
        user.third_app = user.ThirdApp.LOCAL_USER.value
        user.last_active = timezone.now()
        user.save(update_fields=['third_app', 'last_active'])
        return r

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class SignOutView(View):
    def get(self, request, *args, **kwargs):
        return self.logout_user(request)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    @staticmethod
    def logout_user(request):
        """
        注销用户
        """
        to = request.GET.get('next')  # 登出后重定向url
        if not to:
            to = resolve_url(settings.LOGOUT_REDIRECT_URL)

        user = request.user
        if user.id:
            logout(request)
            # 科技云通行证用户登录
            if user.third_app == User.ThirdApp.KJY_PASSPORT.value:
                user.third_app = User.ThirdApp.LOCAL_USER.value
                user.save(update_fields=['third_app'])
                next_url = request.build_absolute_uri(location=to)
                return KJYLogin.kjy_logout(next_to=next_url)

        return redirect(to=to)


class ChangePasswordView(View):
    def get(self, request, *args, **kwargs):
        return self.change(request)

    @staticmethod
    def change(request, form=None):
        content = {
            'form_title': _('修改密码'),
            'submit_text': _('确定'),
            'action_url': resolve_url('users:password')
        }

        user = request.user
        # 当前用户为第三方应用登录认证
        if user.third_app != User.ThirdApp.LOCAL_USER.value:
            app_name = user.get_third_app_display()
            if user.password:
                tips_msg = _('您当前是通过第三方应用"%(name)s"登录认证，并且您曾经为此用户设置过本地密码，'
                             '若忘记密码，请通过登录页面找回密码。') % {'name': app_name}
            else:
                content['form_title'] = _('设置密码')
                if form is None:
                    form = forms.PasswordForm()
                tips_msg = _('您当前是通过第三方应用"%(name)s"登录认证，您还未为此用户设置本地密码，你可以通过此页面为此用户'
                             '设置本地密码，以便以后直接本地登录。') % {'name': app_name}
            content['tips_msg'] = tips_msg

        if form is None:
            form = forms.PasswordChangeForm()

        content['form'] = form
        return render(request, 'form.html', content)

    def post(self, request, *args, **kwargs):
        user = request.user
        # 当前用户为第三方应用登录认证
        if user.third_app != User.ThirdApp.LOCAL_USER.value and not user.password:
            form = forms.PasswordForm(request.POST)
        else:
            form = forms.PasswordChangeForm(request.POST, user=request.user)

        if form.is_valid():
            # 修改密码
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save(update_fields=['password', 'last_active'])

            # 注销当前用户，重新登陆
            try:
                login_url = resolve_url('users:local_login')
            except Exception as e:
                login_url = '/'

            if user.third_app == User.ThirdApp.KJY_PASSPORT.value:  # 如果当前是第三方科技云通行证登录认证
                logout(request)
                to = request.build_absolute_uri(location=login_url)
                return KJYLogin.kjy_logout(next_to=to)

            logout(request)
            return redirect(to=login_url)

        return self.change(request, form)


class SignInView(View):
    """
    登录
    """
    def get(self, request, *args, **kwargs):
        kjy_url = KJYLogin.get_kjy_login_url()
        return render(request, 'signin.html', context={'kjy_url': kjy_url})


class EmailDetailView(View):
    """
    邮件详情
    """
    @staticmethod
    def get(request, *args, **kwargs):
        email_id = kwargs.get('email_id')
        email = Email.objects.filter(id=email_id).first()
        return render(request, 'email_detail.html', context={'email': email})
