from django.shortcuts import render
from django.db.models import Count, Subquery
from django.utils.translation import gettext as _

from servers.models import Server, ServiceConfig
from service.managers import UserQuotaManager


def to_int_or_default(val, default=None):
    if not val:
        return default

    try:
        return int(val)
    except ValueError:
        return default


def home(request, *args, **kwargs):
    service_id = to_int_or_default(kwargs.get('service_id'), default=None)
    user = request.user

    servers_qs = Server.objects.filter(user=user)
    servers_count = servers_qs.count()
    if service_id:
        service = ServiceConfig.objects.filter(id=service_id).first()
        is_need_vpn = service.is_need_vpn()
        servers_qs = servers_qs.filter(service=service_id)
    else:
        is_need_vpn = False

    shared_server_count = 0
    private_server_count = 0
    r = servers_qs.values('center_quota').annotate(server_count=Count('id')).order_by()
    for i in r:
        if i['center_quota'] == Server.QUOTA_SHARED:
            shared_server_count = i['server_count']
        elif i['center_quota'] == Server.QUOTA_PRIVATE:
            private_server_count = i['server_count']

    quotas = UserQuotaManager().get_quota_queryset(request.user)
    context = {
        'active_service': service_id,
        'is_need_vpn': is_need_vpn,
        'quotas': quotas,
        'shared_server_count': shared_server_count,
        'private_server_count': private_server_count
    }
    return render(request, 'home.html', context=context)
