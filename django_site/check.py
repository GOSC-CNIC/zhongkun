from core import site_configs_manager


def check_setting():
    try:
        site_configs_manager.get_pay_app_id(check_valid=False)
    except Exception as e:
        print(e)

    try:
        site_configs_manager.get_wallet_rsa_keys()
    except Exception as e:
        print(e)
