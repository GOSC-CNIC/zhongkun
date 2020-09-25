from django import template
from django.core.cache import cache
from django.db.models import Prefetch

from service.models import DataCenter, ServiceConfig

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


@register.simple_tag(name='get_center_and_services')
def do_get_center_and_services():
    cache_key = 'tag_get_center_and_services'
    centers = cache.get(cache_key)
    if centers is None:
        prefetch = Prefetch('service_set', queryset=ServiceConfig.objects.filter(
            status=ServiceConfig.STATUS_ENABLE).all(), to_attr='services')
        qs = DataCenter.objects.filter(status=DataCenter.STATUS_ENABLE).prefetch_related(prefetch).all()
        centers = []
        for c in qs:
            services = []
            for s in c.services:
                services.append({'id': s.id, 'name': s.name})

            centers.append({'id': c.id, 'name': c.name, 'services': services})

        cache.set(cache_key, centers, timeout=120)

    return centers
