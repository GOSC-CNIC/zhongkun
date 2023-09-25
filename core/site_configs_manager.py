from django.conf import settings
from django.utils.translation import gettext


site_configs = getattr(settings, 'WEBSITE_CONFIG', {})


def get_website_brand():
    title = site_configs.get('site_brand')
    if not title:
        title = gettext('中国科技云一体化云服务')

    return title


def get_website_url():
    site_url = site_configs.get('site_url')
    if not site_url:
        site_url = gettext('https://service.cstcloud.cn')

    return site_url


def get_about_us():
    s = site_configs.get('about_us')
    if not s:
        s = gettext('中国科学院计算机网络信息中心，科技云部。')

    return s


website_brand = get_website_brand()
website_url = get_website_url()
about_us = get_about_us()
