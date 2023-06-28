from django import template
from django.utils.translation import gettext
from django.conf import settings


register = template.Library()


@register.simple_tag
def use_kjy_signin():
    tpaa = getattr(settings, 'THIRD_PARTY_APP_AUTH', {})
    return 'SCIENCE_CLOUD' in tpaa


def get_website_header():
    config = getattr(settings, 'WEBSITE_CONFIG', {})
    title = config.get('site_brand')
    if not title:
        title = gettext('中国科技云一体化云服务')

    return title


@register.simple_tag(name='get_website_title')
def do_get_website_title():
    return get_website_header()
