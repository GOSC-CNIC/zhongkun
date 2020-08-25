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
    limit = 5
    service_id = to_int_or_default(kwargs.get('service_id'), default=None)

    # services = ServiceConfig.objects.filter(active=True).all()
    if service_id:
        servers_qs = Server.objects.filter(service=service_id, deleted=False)
        servers = servers_qs[0:limit]
        servers_count = len(servers)
        if servers_count >= limit:
            servers_count = servers_qs.count()
    else:
        servers_qs = Server.objects.filter(deleted=False)
        servers = servers_qs[0:limit]
        servers_count = len(servers)
        if servers_count >= limit:
            servers_count = servers_qs.count()

    context = {
        # 'services': services,
        'servers': servers,
        'active_service': service_id,
        'servers_count': servers_count
    }
    return render(request, 'home.html', context=context)
