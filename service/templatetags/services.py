from django import template
from django.core.cache import cache

from service.models import ServiceConfig

register = template.Library()


@register.simple_tag(name='get_services')
def do_get_services():
    cache_key = 'tag_get_services'
    d = cache.get(cache_key)
    if d is None:
        qs = ServiceConfig.objects.filter(status=ServiceConfig.STATUS_ENABLE).values('id', 'name')
        d = list(qs)
        cache.set(cache_key, d, timeout=120)

    return d
