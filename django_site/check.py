from django.conf import settings

from core import site_configs_manager


def check_setting(screenvis_only: bool):
    site_configs_manager.get_pay_app_id(dj_settings=settings, check_valid=False)

    try:
        site_configs_manager.get_wallet_rsa_keys()
    except Exception as e:
        print(e)
