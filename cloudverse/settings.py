"""
Django settings for yunkun project.

Generated by 'django-admin startproject' using Django 2.2.13.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import sys
from datetime import timedelta
from pathlib import Path

from django.utils.translation import gettext_lazy
from django.conf.locale.zh_Hans import formats as zh_formats
from django.conf.locale.en import formats as en_formats

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']
INTERNAL_IPS = []

# Application definition

INSTALLED_APPS = [
    'baton',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'django_filters',
    # 'rest_framework.authtoken',
    'drf_yasg',
    'corsheaders',
    'django_json_widget',

    'apps.service',
    'apps.storage',
    'apps.servers',
    'apps.order',
    'apps.app_wallet',
    'apps.metering',
    'apps.report',
    'apps.users',
    'apps.vo',
    'apps.ticket',
    'apps.monitor',
    'apps.app_netbox',
    'apps.app_scan',
    'apps.vpn',
    'apps.api',
    'apps.app_apply',
    'apps.app_screenvis',
    'apps.app_global',
    'apps.app_netflow',
    'apps.app_alert',
    # app放上面
    'docs',
    'scripts',
    'baton.autodiscover',
]

# 自定义参数，设置admin后台app的排列顺序
ADMIN_SORTED_APP_LIST = [
    'service',
    'storage',
    'servers',
    'order',
    'bill',     # app_wallet
    'metering',
    'report',
    'ticket',
    'users',
    'vo',
    'monitor',
    'netbox',   # app_netbox
    'scan',     # app_scan
    'vpn',
    'app_screenvis',
    'app_alert',
    'app_netflow',
    'apply',    # app_apply
    'app_global',
    'auth',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cloudverse.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [Path('/').joinpath(BASE_DIR, 'templates'), ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'sitetags': 'templatetags.sitetags'
            }
        },
    },
]

WSGI_APPLICATION = 'cloudverse.wsgi.application'

# CACHE
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
# 在文件security.py中配置


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

# 日期时间显示格式
TIME_INPUT_FORMATS = [
    "%H:%M:%S",  # '14:30:59'   # admin 后台时间的编辑格式会选第一个，精确到秒
    "%H:%M:%S.%f",  # '14:30:59.000200'
    "%H:%M",  # '14:30'
]
DATE_FORMAT = 'Y-m-d'
TIME_FORMAT = "H:i:s"  # 20:45:01
DATETIME_FORMAT = "Y-m-d H:i:s"  # 2016年9月5日 20:45

# USE_L10N = True, 国际化时，各语言的设置优先级高于全局
zh_formats.DATE_FORMAT = "Y年m月d日"  # 2016年9月5日
zh_formats.TIME_FORMAT = TIME_FORMAT
zh_formats.DATETIME_FORMAT = 'Y年m月d日 H:i:s'
zh_formats.TIME_INPUT_FORMATS = TIME_INPUT_FORMATS

en_formats.DATE_FORMAT = DATE_FORMAT
en_formats.TIME_FORMAT = TIME_FORMAT
en_formats.DATETIME_FORMAT = DATETIME_FORMAT
en_formats.TIME_INPUT_FORMATS = TIME_INPUT_FORMATS

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LANGUAGES = [
    ('zh-hans', 'Simplified Chinese'),
    ('en', 'English')
]
# 翻译文件所在目录
LOCALE_PATHS = (
    Path('/').joinpath(BASE_DIR, 'locale'),
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = Path('/').joinpath(BASE_DIR, 'collect_static')
# 静态文件查找路径
STATICFILES_DIRS = [
    Path('/').joinpath(BASE_DIR, 'static'),
]

MEDIA_ROOT = Path('/').joinpath(BASE_DIR, 'media')

# session 有效期设置
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # True：关闭浏览器，则Cookie失效。
# SESSION_COOKIE_AGE=60*30   #30分钟

# 自定义用户模型
AUTH_USER_MODEL = 'users.UserProfile'

# 避免django把未以/结尾的url重定向到以/结尾的url
# APPEND_SLASH=False

# 登陆url
LOGIN_URL = '/accounts/local_login/'
LOGOUT_URL = '/accounts/logout/'
LOGIN_REDIRECT_URL = '/'  # 默认重定向url
LOGOUT_REDIRECT_URL = '/'

# 第三方应用登录认证，不支持那种认证 注释掉
THIRD_PARTY_APP_AUTH = {
    # 科技云通行证
    'SCIENCE_CLOUD': {
        'name': gettext_lazy('中国科技云通行证'),  # 登录页面显示的名称
        'client_home_url': 'https://yunkun.cstcloud.cn',
        'client_callback_url': 'https://yunkun.cstcloud.cn/accounts/callback/',  # 认证回调地址
        'login_url': 'https://passport.escience.cn/oauth2/authorize?response_type=code&theme=embed',
        'token_url': 'https://passport.escience.cn/oauth2/token',
        'logout_url': 'https://passport.escience.cn/logout'
    },
    # AAI
    'AAI': {
        'name': gettext_lazy('中国科技云身份认证联盟'),  # 登录页面显示的名称
        'client_home_url': 'https://yunkun.cstcloud.cn',
        'client_callback_url': 'https://yunkun.cstcloud.cn/auth/callback/aai',  # 认证回调地址
        'login_url': 'https://aai.cstcloud.net/oidc/authorize?response_type=code',
        'token_url': 'https://aai.cstcloud.net/oidc/token',
        'user_info_url': 'https://aai.cstcloud.net/oidc/userinfo'
    },
}

REST_FRAMEWORK = {
    'PAGE_SIZE': 100,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.aai.authentication.CreateUserJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication'
    ),
    'EXCEPTION_HANDLER': 'apps.api.viewsets.exception_handler',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

LOGGING_FILES_DIR = Path('/var/log/yunkun')
if not LOGGING_FILES_DIR.exists():
    LOGGING_FILES_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'dubug_formatter': {
            'format': '%(levelname)s %(asctime)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        # # logging file settings
        'file': {
            'level': 'WARNING',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': LOGGING_FILES_DIR.joinpath('yunkun.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 50,  # 50MB
            'backupCount': 5  # 最多5个文件
        },
        # output to console settings
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],  # working with debug mode
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'loggers': {
        # 'django.db.backends': {
        #     'handlers': ['console'],
        #     'propagate': True,
        #     'level': 'DEBUG',
        # },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',  # 'ERROR',
            'propagate': False,
        },
    },
}

PASSPORT_JWT = {
    'ALGORITHM': 'RS512',
    'SIGNING_KEY': '',
    # 'VERIFYING_KEY': None,
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'username',
    'USER_ID_CLAIM': 'email',  # 'cstnetId','email'
    'AAI_USER_ID': 'id',  # 科技云通行证/AAI中user id在jwt中的字段名称
    'TOKEN_TYPE_CLAIM': 'type',
    'EXPIRATION_CLAIM': 'exp',

    # 'JTI_CLAIM': 'jti'

    # passort jwt field
    'ORG_NAME_FIELD': 'orgName',
    'TRUE_NAME_FIELD': 'name'
}

# drf-yasg
SWAGGER_SETTINGS = {
    # 'LOGIN_URL': reverse_lazy('admin:login'),
    # 'LOGOUT_URL': '/admin/logout',
    'USE_SESSION_AUTH': True,
    'PERSIST_AUTH': True,
    'REFETCH_SCHEMA_WITH_AUTH': True,
    'REFETCH_SCHEMA_ON_LOGOUT': True,

    'SECURITY_DEFINITIONS': {
        'Basic': {
            'type': 'basic'
        },
        'Bearer': {
            'in': 'header',
            'name': 'Authorization',
            'type': 'apiKey',
        }
    },
    'DOC_EXPANSION': 'none',
}

# admin
BATON = {
    'COPYRIGHT': '',  # noqa
    'POWERED_BY': '<a href="https://gitee.com/cstcloud-cnic">CNIC</a>',
    'MENU_ALWAYS_COLLAPSED': True,
    'CHANGELIST_FILTERS_IN_MODAL': False,
    'CHANGELIST_FILTERS_ALWAYS_OPEN': False,
    'CHANGELIST_FILTERS_FORM': True,
    'GRAVATAR_ENABLED': False,
}

# swagger api在线文档地址配置
SWAGGER_SCHEMA_URL = None  # 'https://xxx.xxx'

# 跨域
# CORS_ALLOWED_ORIGINS = [
#     "https://example.com",
# ]

CORS_ALLOW_ALL_ORIGINS = True  # 允许所有请求来源跨域

# 站点的一些全局配置
WEBSITE_CONFIG = {
    'site_brand': gettext_lazy('中国科技云一体化云服务平台'),  # 本站点的名称，一些邮件通知也会用到
    'site_url': 'https://service.cstcloud.cn',  # 本站点的地址，一些邮件通知也会用到
    'about_us': '',  # gettext_lazy(''),     # “关于”网页中“关于我们”的文字描述
}

# crontab定时任务设置，每任务项的第一个值是任务的标签字符串，必须以“task”开头
# 任务管理命令 python3 manage.py crontabtask add/remove/show
CRONTABJOBS = [
    ('task1_metering', '0 9 * * *',
     'python3 /home/uwsgi/yunkun/scripts/timedelta_metering.py >> /var/log/yunkun/task_metering.log'),
    ('task2_bkt_monthly', '0 12 28 * *',
     'python3 /home/uwsgi/yunkun/scripts/run_bucket_monthly_stats.py',),
    ('task3_monthly_report', '0 17 28 * *',
     'python3 /home/uwsgi/yunkun/scripts/run_generate_and_email_month_report.py >> /var/log/yunkun/task_monthly_report.log'),
    ('task4_logsite_timecount', '*/1 * * * *',
     'python3 /home/uwsgi/yunkun/scripts/run_log_site_req_num.py >> /var/log/yunkun/task_logsite_timecount.log'),
    ('task5_req_num', '0 */1 * * *',
     'python3 /home/uwsgi/yunkun/scripts/update_service_req_num.py >> /var/log/yunkun/task_update_req_num.log'),
    ('task6_scan_start', '*/3 * * * *',
     'python3 /home/uwsgi/yunkun/scripts/run_scan_process.py >> /var/log/yunkun/task_scan_process.log'),
    ('task7_screen_host_cpuusage', '*/3 * * * *',
     'python3 /home/uwsgi/yunkun/scripts/run_screen_host_cpuusage.py >> /var/log/yunkun/task_screen_host_cpuusage.log'),
    ('task8_alert_email_notification', '*/1 * * * *',
     'python3 /home/uwsgi/yunkun/apps/app_alert/scripts/alert_email_notification.py >> /var/log/yunkun/task_alert_email_notification.log'),
    ('task9_alert_dingtalk_notification', '*/1 * * * *',
     'python3 /home/uwsgi/yunkun/apps/app_alert/scripts/alert_dingtalk_notification.py >> /var/log/yunkun/task_alert_dingtalk_notification.log'),
    ('task10_screen_service_stats.py', '*/3 * * * *',
     'python3 /home/uwsgi/yunkun/scripts/run_screen_service_stats.py >> /var/log/yunkun/task_screen_service_stats.log'),
]

# 安全配置导入
from .security import *

if DEBUG:
    from .test_settings import TEST_CASE

    # django debug toolbar
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
    DEBUG_TOOLBAR_CONFIG = {
        # 'SHOW_COLLAPSED': True,
    }
    INTERNAL_IPS += ['127.0.0.1']  # 通过这些IP地址访问时，页面才会出现django debug toolbar面板
