from utils.crypto.rsa import generate_rsa_key
from apps.app_global.configs_manager import global_configs
from apps.app_global.models import GlobalConfig
from apps.app_wallet.models import PayApp


def set_wallet_rsa_keys_for_test():
    private_key, public_key = generate_rsa_key()
    pri_key_obj, created = GlobalConfig.objects.update_or_create(
        name=GlobalConfig.ConfigName.WALLET_RSA_PRIVATE_KEY.value,
        defaults={'value': private_key}
    )
    pub_key_obj, created = GlobalConfig.objects.update_or_create(
        name=GlobalConfig.ConfigName.WALLET_RSA_PUBLIC_KEY.value,
        defaults={'value': public_key}
    )
    global_configs.clear_cache()
    return private_key, public_key


def register_and_set_app_id_for_test():
    app_name = 'test-app'
    app = PayApp.objects.filter(name=app_name).first()
    if app is None:
        app = PayApp(name=app_name)
        app.save(force_insert=True)

    obj, created = GlobalConfig.objects.update_or_create(
        name=GlobalConfig.ConfigName.PAYMENT_APP_ID.value,
        defaults={'value': app.id}
    )
    global_configs.clear_cache()
    return app
