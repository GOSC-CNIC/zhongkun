from django.shortcuts import render
from django.views import View

from .models import ServiceConfig, Server
from api import auth


def index(request, *args, **kwargs):
    servers = Server.objects.filter(deleted=False).all()

    return render(request, 'index.html', {'servers': servers})


class ServerCreateView(View):
    def get(self, request, *args, **kwargs):
        services = ServiceConfig.objects.filter(active=True).all()
        service = services[0]
        adapter = auth.get_adapter(service)
        headers = auth.get_auth_header(service)
        g = adapter.list_groups(region_id=service.region_id, headers=headers)
        flavors = adapter.list_flavors(headers=headers)

        context = {
            'services': services,
            'flavors': flavors['results'],
            'groups': g['results']
        }
        return render(request, 'create.html', context=context)
