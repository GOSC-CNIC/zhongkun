import requests
from django.shortcuts import render
from django.views import View

from apps.app_probe.models import ProbeDetails, ProbeMonitorWebsite


# Create your views here.


class ProbeDetailsViews(View):

    def get(self, request, *args, **kwargs):

        # 探针信息
        probe = ProbeDetails().get_instance()

        web_task = ProbeMonitorWebsite.objects.all()
        return render(request, 'index.html', context={'probe': probe, 'web_task': web_task})
