from django.urls import reverse

from utils.test import get_or_create_service
from apps.app_monitor.models import TotalReqNum
from apps.api.apiviews.portal_views import PortalIPRestrictor
from . import MyAPITestCase, get_or_create_user


def add_portal_allowed_ip(real_ip: str = '127.0.0.1'):
    PortalIPRestrictor.add_ip_rule(real_ip)
    PortalIPRestrictor.clear_cache()


def clear_portal_allowed_ips():
    PortalIPRestrictor.remove_ip_rules(ip_values=['127.0.0.1'])
    PortalIPRestrictor.clear_cache()


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
        self.assertIsNone(response.data['until_time'])

        ins = TotalReqNum.get_instance(TotalReqNum.ServiceType.OWN.value)
        ins.req_num = 6688
        ins.save(update_fields=['req_num'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 6688)
        self.assertIsNotNone(response.data['until_time'])

        vms_ins = TotalReqNum.get_instance(TotalReqNum.ServiceType.VMS.value)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 6688)
        self.assertIsNotNone(response.data['until_time'])

        obs_ins = TotalReqNum.get_instance(TotalReqNum.ServiceType.OBS.value)
        obs_ins.req_num = 134634
        obs_ins.save(update_fields=['req_num'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 6688 + 134634)
        self.assertIsNotNone(response.data['until_time'])

        vms_ins.req_num = 56758
        vms_ins.save(update_fields=['req_num'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 6688 + 134634 + 56758)
        self.assertIsNotNone(response.data['until_time'])


class PortalVmsTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')
        self.service = get_or_create_service()
        clear_portal_allowed_ips()

    def test_status(self):
        base_url = reverse('api:portal-vms-status')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['status'], 'success')

    def test_user_num(self):
        base_url = reverse('api:portal-vms-user-num')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['count'], 1)

    def test_req_num(self):
        base_url = reverse('api:portal-vms-total-req-num')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 0)
        self.assertTrue(response.data['until_time'])

        ins = TotalReqNum.get_instance(TotalReqNum.ServiceType.VMS.value)
        ins.req_num = 6688
        ins.save(update_fields=['req_num'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 6688)


class PortalObsTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')
        self.service = get_or_create_service()
        clear_portal_allowed_ips()

    def test_status(self):
        base_url = reverse('api:portal-obs-status')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['status'], 'success')

    def test_user_num(self):
        base_url = reverse('api:portal-obs-user-num')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['count'], 1)

    def test_req_num(self):
        base_url = reverse('api:portal-obs-total-req-num')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        add_portal_allowed_ip()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 0)
        self.assertTrue(response.data['until_time'])

        ins = TotalReqNum.get_instance(TotalReqNum.ServiceType.OBS.value)
        ins.req_num = 6688
        ins.save(update_fields=['req_num'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['num'], 6688)
