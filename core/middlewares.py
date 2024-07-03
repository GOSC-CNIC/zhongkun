import ipaddress

from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext as _
from django.http.response import HttpResponseForbidden

from core import errors
from apps.app_global.configs_manager import IPAccessWhiteListManager
from utils.iprestrict import IPRestrictor


class AdminIPRestrictor(IPRestrictor):
    def load_ip_rules(self):
        whitelist = IPAccessWhiteListManager.get_module_ip_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.ADMIN.value)
        if not whitelist:
            whitelist = [ipaddress.IPv4Network('0.0.0.0/0')]

        return whitelist

    def check_restricted(self, request):
        """
        :return:
            ip: str
        :raises: AccessDenied
        """
        client_ip, proxy_ips = self.get_remote_ip(request)
        try:
            self.is_restricted(client_ip=client_ip)
        except errors.AccessDenied as exc:
            raise errors.AccessDenied(message=_("拒绝从IP地址'%s'访问后台") % (client_ip,))

        return client_ip


class CloseCsrfMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.csrf_processing_done = True  # csrf处理完毕


class AdminIPRestrictorMiddleware(MiddlewareMixin):

    admin_url = '/admin'    # 限制访问的后台地址

    def __call__(self, request):
        if request.path.startswith(self.admin_url):
            try:
                AdminIPRestrictor().check_restricted(request=request)
            except errors.AccessDenied as exc:
                return HttpResponseForbidden(str(exc))

        response = self.get_response(request)
        return response
