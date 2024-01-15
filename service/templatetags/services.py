from django import template
from django.core.cache import cache

from servers.models import ServiceConfig

register = template.Library()


@register.simple_tag(name='get_services')
def do_get_services():
    cache_key = 'tag_get_services'
    d = cache.get(cache_key)
    if d is None:
        qs = ServiceConfig.objects.filter(status=ServiceConfig.Status.ENABLE).values('id', 'name')
        d = list(qs)
        cache.set(cache_key, d, timeout=120)

    return d


@register.simple_tag(name='get_center_and_services')
def do_get_center_and_services():
    cache_key = 'tag_get_center_and_services'
    centers = cache.get(cache_key)
    if centers is None:
        org_dict = {}
        service_qs = ServiceConfig.objects.select_related(
            'org_data_center__organization').filter(status=ServiceConfig.Status.ENABLE).all()
        sorted_services = sorted(service_qs, key=lambda x: x.sort_weight, reverse=False)
        for s in sorted_services:
            s_data = {'id': s.id, 'name': s.name, 'service_type': s.service_type, 'sort_weight': s.sort_weight}
            org = s.org_data_center.organization if s.org_data_center else None
            if org:
                key = org.id
                if key not in org_dict:
                    org_dict[key] = {'id': org.id, 'name': org.name, 'sort_weight': org.sort_weight, 'services': []}
            else:
                key = None
                if key not in org_dict:
                    org_dict[key] = {'id': '', 'name': '无', 'sort_weight': 0, 'services': []}

            org_dict[key]['services'].append(s_data)

        centers = sorted(org_dict.values(), key=lambda x: x['sort_weight'], reverse=False)
        cache.set(cache_key, centers, timeout=120)

    return centers
