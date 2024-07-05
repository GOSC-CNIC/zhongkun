from django.conf import settings

from core import site_configs_manager


def check_setting(screenvis_only: bool):
    site_configs_manager.get_pay_app_id(dj_settings=settings, check_valid=False)

    payment_rsa = getattr(settings, 'PAYMENT_RSA2048', {})
    private_key = payment_rsa.get('private_key')
    if not private_key:
        raise Exception(f'Not set PAYMENT_RSA2048 private_key')

    public_key = payment_rsa.get('public_key')
    if not public_key:
        raise Exception(f'Not set PAYMENT_RSA2048 public_key')
