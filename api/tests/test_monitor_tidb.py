from urllib import parse

from django.urls import reverse
from django.utils import timezone

from service.models import DataCenter
from monitor.models import (
    MonitorJobTiDB, MonitorProvider
)

from utils.test import get_or_create_user
from . import MyAPITestCase


class MonitorUnitTiDBTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')

    def test_list_unit(self):
        provider = MonitorProvider()
        provider.save(force_insert=True)
        org = DataCenter(
            name='test', name_en='test en', abbreviation='t', creation_time=timezone.now()
        )
        org.save(force_insert=True)
        unit_tidb1 = MonitorJobTiDB(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            provider=provider, organization=org
        )
        unit_tidb1.save(force_insert=True)

        unit_tidb2 = MonitorJobTiDB(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
            provider=provider, organization=org
        )
        unit_tidb2.save(force_insert=True)

        unit_tidb3 = MonitorJobTiDB(
            name='name3', name_en='name_en3', job_tag='job_tag3', sort_weight=3,
            provider=provider
        )
        unit_tidb3.save(force_insert=True)

        unit_tidb4 = MonitorJobTiDB(
            name='name4', name_en='name_en4', job_tag='job_tag4',  sort_weight=8,
            provider=provider
        )
        unit_tidb4.save(force_insert=True)

        # 未认证
        url = reverse('api:monitor-unit-tidb-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # 没有管理权限
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # unit_tidb4
        unit_tidb4.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(['id', "name", "name_en", "job_tag", 'creation', 'remark',
                           'sort_weight', 'grafana_url', 'dashboard_url', 'organization'], response.data['results'][0])
        self.assertEqual(unit_tidb4.id, response.data['results'][0]['id'])
        self.assertIsNone(response.data['results'][0]['organization'])

        # unit_tidb1, unit_tidb4
        unit_tidb1.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_tidb1.id, response.data['results'][0]['id'])
        self.assertKeysIn(['id', "name", "name_en", "abbreviation", 'creation_time', 'sort_weight'
                           ], response.data['results'][0]['organization'])

        # unit_tidb1, unit_tidb4, unit_tidb2
        unit_tidb2.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(unit_tidb1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_tidb4.id, response.data['results'][1]['id'])
        self.assertEqual(unit_tidb2.id, response.data['results'][2]['id'])

        # query "organization_id"
        query = parse.urlencode(query={'organization_id': org.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_tidb1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_tidb2.id, response.data['results'][1]['id'])

        # page_size
        query = parse.urlencode(query={'page': 1, 'page_size': 2})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_tidb1.id, response.data['results'][0]['id'])

        # federal_admin
        self.user.set_federal_admin()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(unit_tidb1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_tidb4.id, response.data['results'][1]['id'])
        self.assertEqual(unit_tidb2.id, response.data['results'][2]['id'])
        self.assertEqual(unit_tidb3.id, response.data['results'][3]['id'])

        # query "organization_id"
        query = parse.urlencode(query={'organization_id': org.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_tidb1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_tidb2.id, response.data['results'][1]['id'])
