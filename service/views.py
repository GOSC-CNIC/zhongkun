from django.shortcuts import render

from servers.models import Server, ServiceConfig


def to_int_or_default(val, default=None):
    if not val:
        return default

    try:
        return int(val)
    except ValueError:
        return default


def home(request, *args, **kwargs):
    service_id = to_int_or_default(kwargs.get('service_id'), default=None)

    services = ServiceConfig.objects.filter(active=True).all()
    if service_id:
        servers_count = Server.objects.filter(service=service_id, deleted=False).count()
    else:
        servers_count = Server.objects.filter(deleted=False).count()

    context = {
        'services': services,
        'active_service': service_id,
        'servers_count': servers_count
    }
    return render(request, 'home.html', context=context)
