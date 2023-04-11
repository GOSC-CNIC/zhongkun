# 敏感信息配置文件security.py的demo
from .settings import PASSPORT_JWT

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'xxx'


# # Database
# # https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # 数据库引擎
        'NAME': 'xxx',  # 数据的库名，事先要创建之
        'HOST': '127.0.0.1',  # 主机
        'PORT': '3306',  # 数据库使用的端口
        'USER': 'xxx',  # 数据库用户名
        'PASSWORD': 'xxx',  # 密码
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES';",   # SET foreign_key_checks = 0;
            'charset': 'utf8mb4'
        },
        'TEST': {
            'NAME': 'testvms',     # unit test database
            'CHARSET': 'utf8mb4'
        },
    },
}

# 第三方应用登录认证敏感信息
THIRD_PARTY_APP_AUTH_SECURITY = {
    # 科技云通行证
    'SCIENCE_CLOUD': {
        'client_id': 0,
        'client_secret': 'xxx',
    },
}

# 邮箱配置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True    # 是否使用TLS安全传输协议
# EMAIL_PORT = 25
EMAIL_HOST = 'xxx'
EMAIL_HOST_USER = 'xxx'
EMAIL_HOST_PASSWORD = 'xxx'


# 科技云通行证JWT认证公钥
PASSPORT_JWT['VERIFYING_KEY'] = 'xxx'


# 钱包结算服务RSA Key，加签验签
PAYMENT_RSA2048 = {
    'private_key': """
-----BEGIN PRIVATE KEY-----
xxx
-----END PRIVATE KEY-----
""",
    'public_key': """
-----BEGIN PUBLIC KEY-----
xxx
-----END PUBLIC KEY-----  
"""
}


# 余额支付配置
PAYMENT_BALANCE = {
    'app_id': 'xxx'
}

# test case settings
TEST_CASE_SECURITY = {
    'SERVICE': {
        'endpoint_url': 'http://127.0.0.1/',
        'region_id': 1,
        'service_type': 'evcloud',
        'username': 'xxx',
        'password': 'xxx',
        'version': 'v3',
    },
    'STORAGE_SERVICE': {
        'endpoint_url': 'http://159.226.235.188:8001/',
        'service_type': 'iharbor',
        'username': 'test',
        'password': 'test123456',
        'version': 'v1',
    }
}
