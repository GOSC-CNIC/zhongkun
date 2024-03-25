from django.urls import reverse
from django.conf import settings

from utils.test import get_or_create_service
from monitor.models import TotalReqNum
from api.apiviews.portal_views import PortalIPRestrictor
from . import MyAPITestCase, get_or_create_user


def add_portal_allowed_ip(real_ip: str = '127.0.0.1'):
    settings.API_KJY_PORTAL_ALLOWED_IPS = [real_ip]
    ip_rt = PortalIPRestrictor()
    ip_rt.reload_ip_rules()
    PortalIPRestrictor.allowed_ips = ip_rt.allowed_ips


def clear_portal_allowed_ips():
    settings.API_KJY_PORTAL_ALLOWED_IPS = []
    PortalIPRestrictor.allowed_ips = []


class PortalServiceTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')
        self.service = get_or_create_service()
        clear_portal_allowed_ips()

    def test_status(self):
        base_url = reverse('api:portal-service-status')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['status'], 'success')

    def test_user_num(self):
        base_url = reverse('api:portal-service-user-num')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['count'], 1)

    def test_req_num(self):
        base_url = reverse('api:portal-service-total-req-num')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 0)
        self.assertTrue(response.data['until_time'])

        ins = TotalReqNum.get_instance()
        ins.req_num = 6688
        ins.save(update_fields=['req_num'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 6688)
