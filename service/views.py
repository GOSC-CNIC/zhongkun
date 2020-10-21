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

    quota = UserQuotaManager().get_quota(request.user)
    labels_server = f"""["{_('共享已建')}", "{_('共享可建')}", "{_('私有已建')}"]"""
    if quota.all_ip_count <= 0 and shared_server_count <= 0 and private_server_count <= 0:
        data_server = """[0.1, 0, 0]"""
    else:
        can_create = max(quota.all_ip_count - servers_count, 0)
        data_server = f"[{shared_server_count}, {can_create}, {private_server_count}]"

    context = {
        'active_service': service_id,
        'is_need_vpn': is_need_vpn,
        'quota': quota,
        'shared_server_count': shared_server_count,
        'private_server_count': private_server_count,
        'labels_server': labels_server,
        'data_server': data_server
    }
    return render(request, 'home.html', context=context)
