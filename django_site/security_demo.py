# 敏感信息配置文件security.py的demo

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'xxx'

# # Database
# # https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # MySQL数据库
        # 'ENGINE': 'django_tidb',    # TiDB数据库，推荐7.5+及以上
        'NAME': 'xxx',  # 数据的库名，事先要创建之
        'HOST': '127.0.0.1',  # 主机
        'PORT': '3306',  # 数据库使用的端口
        'USER': 'xxx',  # 数据库用户名
        'PASSWORD': 'xxx',  # 密码
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES';",  # SET foreign_key_checks = 0;
            'charset': 'utf8mb4'
        },
        'TEST': {
            'NAME': 'testvms',  # unit test database
            'CHARSET': 'utf8mb4'
        },
    },
}


# 邮箱配置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True  # 是否使用TLS安全传输协议
# EMAIL_PORT = 25
EMAIL_HOST = 'xxx'
EMAIL_HOST_USER = 'xxx'
EMAIL_HOST_PASSWORD = 'xxx'


# api限制客户端ip访问设置
# X-Forwarded-For 可能伪造，需要在服务一级代理防范处理
# 比如nginx：
# uwsgi_param X-Forwarded-For $remote_addr;     不能使用 $proxy_add_x_forwarded_for;
# proxy_set_header X-Forwarded-For $remote_addr;     不能使用 $proxy_add_x_forwarded_for;
# ip设置规则允许 单个ip、一个网段、一个ip段，如'192.168.1.1'、 '192.168.1.1/24'、'192.168.1.66 - 192.168.1.100'

# 监控各单元用户邮件地址查询相关接口客户端IP鉴权配置
API_MONITOR_EMAIL_ALLOWED_IPS = []

# 各种服务总请求数统计依赖设置，配置各站点loki日志服务接口，总请求数==各站点的请求数的和
PORTAL_REQ_NUM_LOKI_SITES_MAP = {
    # 本服务
    'own': [
        {'api': 'https://xx.xx.cn/loki/api/v1/query', 'job': 'xx_log'},
    ],
    # 云主机
    'vms': [
        {'api': 'https://xxx.xxx.cn/loki/api/v1/query', 'job': 'xx_log'},
        {'api': 'https://xx.xx.cn/loki/api/v1/query', 'job': 'xx_log'},
    ],
    # 对象存储
    'obs': [
        {'api': 'http://10.0.91.149:34135/loki/api/v1/query', 'job': 'obs'},
    ],
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

DINGTALKROBOT = {
    "WEBHOOK": "https://oapi.dingtalk.com/robot/send?access_token=xxxx",
    "SECRET": "xxx"
}

EASY_OPS = {
    "DOMAIN": 'xxx',
    "USERNAME": "xxx",
    "PASSWORD": "xxx"
}
