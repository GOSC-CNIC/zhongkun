from django.shortcuts import render
from django.views import View

from .models import ServiceConfig, Server


def index(request, *args, **kwargs):
    servers = Server.objects.filter(deleted=False).all()
    return render(request, 'index.html', {'servers': servers})


class ServerCreateView(View):
    def get(self, request, *args, **kwargs):
        services = ServiceConfig.objects.filter(active=True).all()
        return render(request, 'create.html', context={'services': services})
