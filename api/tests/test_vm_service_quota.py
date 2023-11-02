from urllib import parse

from django.urls import reverse
from utils.test import get_or_create_user, get_or_create_service

from service.models import ServiceConfig
from service.managers import ServicePrivateQuotaManager, ServiceShareQuotaManager
from . import MyAPITransactionTestCase, set_auth_header


class VmServiceQuotaTests(MyAPITransactionTestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='service2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False
        )
        self.service2.save(force_insert=True)

    def test_list_service_private_quota(self):
        url = reverse('api:vms-service-p-quota-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # service private quota create
        ServicePrivateQuotaManager().get_quota(service=self.service)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(keys=[
            "private_ip_total", "public_ip_total", "vcpu_total",
            "ram_total", "disk_size_total", "private_ip_used",
            "public_ip_used", "vcpu_used", "ram_used",
            "disk_size_used", "creation_time", "enable", "service"
        ], container=response.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=response.data['results'][0]['service'])
        self.assertEqual(response.data['results'][0]['service']['id'], self.service.id)

        # service2 private quota create
        ServicePrivateQuotaManager().get_quota(service=self.service2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        # service deleted
        self.service.status = self.service.Status.DELETED.value
        self.service.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)

        # service2 disable
        self.service2.status = self.service.Status.DISABLE.value
        self.service2.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)

        # param 'service_id'
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'service_id': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'service_id': self.service2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)

        # service enable
        self.service.status = self.service.Status.ENABLE.value
        self.service.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        ServicePrivateQuotaManager().increase(service=self.service2, ram_gib=2)
        ServicePrivateQuotaManager().deduct(service=self.service2, ram_gib=1)
        query = parse.urlencode(query={'service_id': self.service2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ram_total'], 2)
        self.assertEqual(response.data['results'][0]['ram_used'], 1)

        self._param_data_center_id_test(url=url)

    def _param_data_center_id_test(self, url: str):
        # data_center_id
        query = parse.urlencode(query={'data_center_id': self.service.org_data_center.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'data_center_id': 'xx'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={
            'data_center_id': self.service.org_data_center.organization_id, 'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_service_share_quota(self):
        url = reverse('api:vms-service-s-quota-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # service share quota create
        ServiceShareQuotaManager().get_quota(service=self.service)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(keys=[
            "private_ip_total", "public_ip_total", "vcpu_total",
            "ram_total", "disk_size_total", "private_ip_used",
            "public_ip_used", "vcpu_used", "ram_used",
            "disk_size_used", "creation_time", "enable", "service"
        ], container=response.data['results'][0])
        self.assertEqual(response.data['results'][0]['service']['id'], self.service.id)
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=response.data['results'][0]['service'])

        # service2 share quota create
        ServiceShareQuotaManager().get_quota(service=self.service2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        # service deleted
        self.service.status = self.service.Status.DELETED.value
        self.service.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)
        self.assertEqual(len(response.data['results']), 1)

        # service2 disable
        self.service2.status = self.service.Status.DISABLE.value
        self.service2.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)
        self.assertEqual(len(response.data['results']), 1)

        # param 'service_id'
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'service_id': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        self.assertEqual(response.data['count'], 0)

        query = parse.urlencode(query={'service_id': self.service2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)
        self.assertEqual(len(response.data['results']), 1)

        # service enable
        self.service.status = self.service.Status.ENABLE.value
        self.service.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)

        ServiceShareQuotaManager().increase(service=self.service2, ram_gib=4)
        ServiceShareQuotaManager().deduct(service=self.service2, ram_gib=3)
        query = parse.urlencode(query={'service_id': self.service2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ram_total'], 4)
        self.assertEqual(response.data['results'][0]['ram_used'], 3)

        # data_center_id
        self._param_data_center_id_test(url=url)
