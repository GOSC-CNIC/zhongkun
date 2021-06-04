from django.shortcuts import render
from django.views import View

from core.request import request_vpn_service
from core import errors as exceptions
from service.models import ServiceConfig
from utils.time import iso_to_datetime


class VPNView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        service_id = kwargs.get('service_id')
        service = ServiceConfig.objects.filter(id=service_id).first()

        vpn = None
        err = ''
        if service:
            try:
                r = request_vpn_service(service=service, method='get_vpn_or_create', username=user.username)
                vpn = self.parse_data(data=r)
            except exceptions.APIException as e:
                err = f'Get VPN error, {str(e)}'
        else:
            err = 'not found service'

        context = {
            'active_service': service_id,
            'vpn': vpn,
            'err': err
        }
        if not err:
            config_file_url = request_vpn_service(service=service, method='get_vpn_config_file_url')
            ca_file_url = request_vpn_service(service=service, method='get_vpn_ca_file_url')
            context['vpn_config_file_url'] = config_file_url
            context['vpn_ca_file_url'] = ca_file_url

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

