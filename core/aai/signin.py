from urllib import parse

import requests
from django.shortcuts import redirect
from django.utils.encoding import force_str
from django.utils import timezone as dj_timezone
from django.contrib.auth import login
from django.core.validators import URLValidator, ValidationError

from apps.users.models import UserProfile
from apps.app_global.configs_manager import global_configs


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


class AAISignIn:
    @classmethod
    def as_view(cls):
        return cls().aai_login_callback

    def aai_login_callback(self, request, *args, **kwargs):
        """
        第三方科技云认证联盟aai登录回调视图
        """
        code = request.GET.get('code', None)
        if not code:
            return self.aai_signin_failed()

        try:
            data = self.get_auth_token(code=code)
            user = self.get_or_create_auth_user(token=data['access_token'])
        except Exception as exc:
            return self.aai_signin_failed()

        # 标记当前为科技云通行证登录用户
        if user.third_app != user.ThirdApp.AAI.value:
            user.third_app = user.ThirdApp.AAI.value
            user.last_active = dj_timezone.now()
            user.save(update_fields=['third_app', 'last_active'])

        login(request, user)  # 登录用户
        return redirect(to='/')

    def get_or_create_auth_user(self, token):
        """
        查询或创建登录认证的用户

        :param token:  科技云通行证登录认证token
        :return:
            User()
        :raises: Exception
        """
        user_info = self.get_user_info_by_token(token)
        org_name = user_info.get('orgName')
        email = user_info.get('email')
        truename = user_info.get('name')

        # 邮箱对应用户是否已存在
        user = UserProfile.objects.filter(username=email).first()
        if user:  # 已存在, 返回用户
            return user

        # 创建用户
        try:
            first_name, last_name = self.get_first_and_last_name(truename)
        except Exception:
            first_name, last_name = '', ''

        user = UserProfile(
            username=email, email=email, first_name=first_name, last_name=last_name,
            company=org_name if org_name else ''
        )
        user.save(force_insert=True)

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
    def get_signin_url():
        """
        获取 aai登录url
        :return:
            success: url
            failed: None
        """
        client_id = global_configs.get(global_configs.ConfigName.AAI_LOGIN_CLIENT_ID.value)
        client_callback_url = global_configs.get(global_configs.ConfigName.AAI_LOGIN_CLIENT_CALLBACK_URL.value)
        login_url = global_configs.get(global_configs.ConfigName.AAI_LOGIN_URL.value)

        try:
            URLValidator(schemes=['http', 'https'])(client_callback_url)
        except ValidationError:
            return None

        params = {
            'client_id': client_id,
            'redirect_uri': client_callback_url,
            'response_type': 'code'
        }
        try:
            url = replace_query_params(url=login_url, params=params)
        except:
            return None

        return url

    @staticmethod
    def get_auth_token(code: str):
        """
        获取登录认证后的token

        :param code: 认证成功后回调url中的param参数code
        :return:
            {
                "access_token": "************",
                "token_type": "Bearer",
                "expires_in": 3599,
                "scope": "openid",
                "id_token": "************"
            }

        :raises: Exception
        """
        client_id = global_configs.get(global_configs.ConfigName.AAI_LOGIN_CLIENT_ID.value)
        client_secret = global_configs.get(global_configs.ConfigName.AAI_LOGIN_CLIENT_SECRET.value)
        client_callback_url = global_configs.get(global_configs.ConfigName.AAI_LOGIN_CLIENT_CALLBACK_URL.value)
        token_url = global_configs.get(global_configs.ConfigName.AAI_LOGIN_TOKEN_URL.value)

        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': client_callback_url,
            'code': code,
            'grant_type': 'authorization_code'
        }

        r = requests.post(url=token_url, data=data)
        if r.status_code == 200:
            return r.json()

        raise Exception('向AAI请求查询access_token失败。' + r.text)

    @staticmethod
    def get_user_info_by_token(access_token: str):
        """
        从token中获取用户信息

        :return:
        {
            "country": "中国",
            "sub": "***",
            "orgName": "上海应用物理所",
            "authorizedClaims": null,
            "userOrgInfo": [
                {
                    "symbol": "***",
                    "domain": "",
                    "name": "***",
                    "enName": "***"
                }
            ],
            "requestedClaims": null,
            "name": "董***",
            "email": "***@qq.com"
        }

        :raises: Exception
        """
        user_info_url = global_configs.get(global_configs.ConfigName.AAI_LOGIN_USER_INFO_URL.value)
        r = requests.get(url=user_info_url, headers={'Authorization': f'Bearer {access_token}'})
        if r.status_code == 200:
            return r.json()

        raise Exception('向AAI请求查询用户信息失败。' + r.text)

    @classmethod
    def aai_signin_failed(cls, next_to=None):
        """
        登出科技云账户

        :param next_to: 登出后重定向的url
        :return:
        """
        url = next_to if next_to else '/'
        return redirect(to=url)
