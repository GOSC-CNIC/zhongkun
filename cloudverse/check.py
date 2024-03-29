from django.conf import settings


def check_setting():
    payment_balance = getattr(settings, 'PAYMENT_BALANCE', {})
    app_id = payment_balance.get('app_id')
    if not app_id:
        raise Exception(f'Not set PAYMENT_BALANCE app_id')

    payment_rsa = getattr(settings, 'PAYMENT_RSA2048', {})
    private_key = payment_rsa.get('private_key')
    if not private_key:
        raise Exception(f'Not set PAYMENT_RSA2048 private_key')

    public_key = payment_rsa.get('public_key')
    if not public_key:
        raise Exception(f'Not set PAYMENT_RSA2048 public_key')
