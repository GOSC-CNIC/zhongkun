from django import template

from servers.models import ServiceConfig

register = template.Library()


@register.simple_tag(name='get_services')
def do_get_services():
    return ServiceConfig.objects.filter(active=True).values('id', 'name')
