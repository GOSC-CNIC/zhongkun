from django.shortcuts import render
from django.views import View

from api.request import request_service
from api import exceptions
from service.models import ServiceConfig
from .models import Article
from utils.time import iso_to_datetime


def usage(request, *args, **kwags):
    """
    vpn使用说明视图
    """
    article_usage = Article.objects.filter(topic=Article.TOPIC_VPN_USAGE).first()
    return render(request, 'article.html', context={'article': article_usage})


class VPNView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        service_id = kwargs.get('service_id')
        service = ServiceConfig.objects.filter(id=service_id).first()

        vpn = None
        err = ''
        if service:
            try:
                r = request_service(service=service, method='get_vpn_or_create', username=user.username)
                vpn = self.parse_data(data=r)
            except exceptions.APIException as e:
                err = str(e)
        else:
            err = 'not found service'

        config_file_url = request_service(service=service, method='get_vpn_config_file_url')
        ca_file_url = request_service(service=service, method='get_vpn_ca_file_url')
        context = {
            'active_service': service_id,
            'vpn': vpn,
            'err': err,
            'vpn_config_file_url': config_file_url,
            'vpn_ca_file_url': ca_file_url
        }
        return render(request, 'vpn.html', context=context)

    @staticmethod
    def parse_data(data):
        create_time = data.get('create_time')
        modified_time = data.get('modified_time')
        if create_time:
            create_time = iso_to_datetime(create_time)
            data['create_time'] = create_time

        if modified_time:
            modified_time = iso_to_datetime(modified_time)
            data['modified_time'] = modified_time

        return data

