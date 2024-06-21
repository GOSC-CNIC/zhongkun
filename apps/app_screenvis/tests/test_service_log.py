from urllib import parse

from django.utils import timezone as dj_timezone
from django.urls import reverse

from apps.app_screenvis.models import (
    DataCenter, ServerService, ObjectService, ObjectServiceLog, ServerServiceLog
)
from apps.app_screenvis.permissions import ScreenAPIIPRestrictor
from . import MyAPITestCase


class ServiceLogTests(MyAPITestCase):
    def setUp(self):
        ScreenAPIIPRestrictor.clear_cache()

    def test_list(self):
        nt = dj_timezone.now()
        dc1 = DataCenter(name='dc1', name_en='dc1', creation_time=nt, update_time=nt)
        dc1.save(force_insert=True)
        dc2 = DataCenter(name='dc2', name_en='dc2', creation_time=nt, update_time=nt)
        dc2.save(force_insert=True)

        server_site1 = ServerService(
            name='site1', name_en='site1 en', data_center=dc1, status=ServerService.Status.ENABLE.value,
            endpoint_url='https://test.com', username='test', sort_weight=1)
        server_site1.set_password(raw_password='test_passwd')
        server_site1.save(force_insert=True)
        server_site2 = ServerService(
            name='site2', name_en='site2 en', data_center=dc2, status=ServerService.Status.DISABLE.value,
            endpoint_url='https://test2.com', username='test2', sort_weight=2)
        server_site2.set_password(raw_password='test_passwd2')
        server_site2.save(force_insert=True)

        obj_site1 = ObjectService(
            name='site1', name_en='site1 en', data_center=dc1, status=ObjectService.Status.DISABLE.value,
            endpoint_url='https://test1.com', username='test2', sort_weight=2)
        obj_site1.set_password(raw_password='test_passwd2')
        obj_site1.save(force_insert=True)
        obj_site2 = ObjectService(
            name='site2', name_en='site2 en', data_center=dc2, status=ObjectService.Status.DISABLE.value,
            endpoint_url='https://test2.com', username='test2', sort_weight=2)
        obj_site2.set_password(raw_password='test_passwd2')
        obj_site2.save(force_insert=True)

        server_log1 = ServerServiceLog(
            username='user1', content='test server1', creation_time=dj_timezone.now(), service_cell=server_site1)
        server_log1.save(force_insert=True)
        server_log2 = ServerServiceLog(
            username='user2', content='test server2', creation_time=dj_timezone.now(), service_cell=server_site2)
        server_log2.save(force_insert=True)

        obj_log1 = ObjectServiceLog(
            username='user1', content='test obj1', creation_time=dj_timezone.now(), service_cell=obj_site1)
        obj_log1.save(force_insert=True)
        obj_log2 = ObjectServiceLog(
            username='user2', content='test obj2', creation_time=dj_timezone.now(), service_cell=obj_site2)
        obj_log2.save(force_insert=True)

        base_url = reverse('screenvis-api:server-user-log-list')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        ScreenAPIIPRestrictor.add_ip_rule(ip_value='127.0.0.1')
        ScreenAPIIPRestrictor.clear_cache()

        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        query = parse.urlencode(query={'server_type': 'test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # server
        query = parse.urlencode(query={'server_type': 'server'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'server_type': 'server'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['content'], 'test server2')
        self.assertEqual(response.data['results'][1]['content'], 'test server1')

        # object
        query = parse.urlencode(query={'server_type': 'object'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'server_type': 'object'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['content'], 'test obj2')
        self.assertEqual(response.data['results'][1]['content'], 'test obj1')
