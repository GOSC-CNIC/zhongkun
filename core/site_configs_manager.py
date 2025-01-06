from django.conf import settings
from django.utils.translation import gettext, get_language
from django.utils.functional import lazy

from apps.app_global.configs_manager import global_configs
from .errors import Error


site_configs = getattr(settings, 'WEBSITE_CONFIG', {})


def get_website_brand(default: str = None):
    try:
        lang = get_language()
        if lang == 'en':
            cfg_key = global_configs.ConfigName.SITE_NAME_EN.value
        else:
            cfg_key = global_configs.ConfigName.SITE_NAME.value

        return global_configs.get(cfg_key)
    except Exception as exc:
        if default:
            return default

        raise exc


def get_website_brand_en():
    return global_configs.get(global_configs.ConfigName.SITE_NAME_EN.value)


get_website_brand_lazy = lazy(get_website_brand, str)


def get_website_url():
    return global_configs.get(global_configs.ConfigName.SITE_FRONT_URL.value)


def get_about_us():
    s = site_configs.get('about_us')
    if not s:
        s = gettext('中国科学院计算机网络信息中心，科技云部。')

    return s


def get_pay_app_id(dj_settings, check_valid: bool = True) -> str:
    """
    本服务订单、计量结算 在钱包中对应的 app id
    """
    payment_balance = getattr(dj_settings, 'PAYMENT_BALANCE', {})
    app_id = payment_balance.get('app_id', None)
    if not app_id:
        raise Error(message='Not set PAYMENT_BALANCE app_id')

    if not isinstance(app_id, str):
        raise Error(message='配置参数PAYMENT_BALANCE app_id 必须是一个字符串')

    if not check_valid:
        return app_id

    if len(app_id) >= 14 and app_id[1:].isdigit():
        return app_id

    raise Error(message='配置参数PAYMENT_BALANCE app_id不是一个有效值')


def get_wallet_rsa_keys():
    """
    获取钱包的密钥对

    :raises: Error
    """
    try:
        private_key = global_configs.get(global_configs.ConfigName.WALLET_RSA_PRIVATE_KEY.value)
        public_key = global_configs.get(global_configs.ConfigName.WALLET_RSA_PUBLIC_KEY.value)
    except Exception as exc:
        raise Error(message=str(exc))

    if not private_key:
        raise Error(message='Not set wallet RSA2048 private_key')

    if not public_key:
        raise Error(message='Not set wallet RSA2048 public_key')

    return private_key, public_key
