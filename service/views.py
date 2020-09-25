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
    user = request.user

    if service_id:
        service = ServiceConfig.objects.filter(id=service_id).first()
        is_need_vpn = service.is_need_vpn()
        servers_qs = Server.objects.filter(service=service_id, user=user)
        servers = servers_qs[0:limit]
        servers_count = len(servers)
        if servers_count >= limit:
            servers_count = servers_qs.count()
    else:
        is_need_vpn = False
        servers_qs = Server.objects.filter(user=user)
        servers = servers_qs[0:limit]
        servers_count = len(servers)
        if servers_count >= limit:
            servers_count = servers_qs.count()

    context = {
        'servers': servers,
        'active_service': service_id,
        'servers_count': servers_count,
        'is_need_vpn': is_need_vpn
    }
    return render(request, 'home.html', context=context)
