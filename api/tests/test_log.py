from urllib import parse

from django.urls import reverse
from django.utils import timezone

from service.models import DataCenter
from monitor.models import (
    LogSite, LogSiteType, MonitorProvider
)
from utils.test import get_or_create_user, get_or_create_service
from . import MyAPITestCase


class LogSiteTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.service1 = get_or_create_service()

    def test_list_unit(self):
        provider = MonitorProvider()
        provider.save(force_insert=True)
        org = DataCenter(
            name='test', name_en='test en', abbreviation='t', creation_time=timezone.now()
        )
        org.save(force_insert=True)

        site_type1 = LogSiteType(name='obj', name_en='obj en', sort_weight=6)
        site_type1.save(force_insert=True)
        log_site1 = LogSite(
            name='name1', name_en='name_en1', log_type=LogSite.LogType.HTTP.value,
            site_type_id=None, job_tag='job_tag1', sort_weight=10,
            provider=provider, organization=None
        )
        log_site1.save(force_insert=True)

        log_site2 = LogSite(
            name='name2', name_en='name_en2', log_type=LogSite.LogType.HTTP.value,
            site_type_id=site_type1.id, job_tag='job_tag2', sort_weight=5,
            provider=provider, organization=org
        )
        log_site2.save(force_insert=True)
        log_site3 = LogSite(
            name='name3', name_en='name_en3', log_type=LogSite.LogType.NAT.value,
            site_type_id=site_type1.id, job_tag='job_tag3', sort_weight=3,
            provider=provider, organization=org
        )
        log_site3.save(force_insert=True)

        log_site4 = LogSite(
            name='name4', name_en='name_en4', log_type=LogSite.LogType.NAT.value,
            site_type_id=site_type1.id, job_tag='job_tag4', sort_weight=8,
            provider=provider, organization=org
        )
        log_site4.save(force_insert=True)

        # 未认证
        url = reverse('api:monitor-log-site-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # 没有管理权限
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # log_site4
        log_site4.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(['id', "name", "name_en", "job_tag", 'creation', 'desc', 'log_type',
                           'sort_weight', 'organization'], response.data['results'][0])
        self.assertEqual(log_site4.id, response.data['results'][0]['id'])
        self.assertKeysIn(['id', "name", "name_en", "abbreviation", 'creation_time', 'sort_weight'
                           ], response.data['results'][0]['organization'])
        self.assertKeysIn(['id', "name", "name_en", 'desc', 'sort_weight'
                           ], response.data['results'][0]['site_type'])

        # log_site4, log_site1
        log_site1.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(log_site1.id, response.data['results'][1]['id'])
        self.assertIsNone(response.data['results'][1]['organization'])
        self.assertIsNone(response.data['results'][1]['site_type'])

        # log_site2, log_site4, log_site1
        log_site2.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(log_site2.id, response.data['results'][0]['id'])
        self.assertEqual(log_site4.id, response.data['results'][1]['id'])
        self.assertEqual(log_site1.id, response.data['results'][2]['id'])

        # page_size
        query = parse.urlencode(query={'page': 1, 'page_size': 2})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(log_site2.id, response.data['results'][0]['id'])

        # federal_admin
        self.user.set_federal_admin()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(log_site3.id, response.data['results'][0]['id'])
        self.assertEqual(log_site2.id, response.data['results'][1]['id'])
        self.assertEqual(log_site4.id, response.data['results'][2]['id'])
        self.assertEqual(log_site1.id, response.data['results'][3]['id'])

        # query "log_type"
        query = parse.urlencode(query={'log_type': LogSite.LogType.HTTP.value})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(log_site2.id, response.data['results'][0]['id'])
        self.assertEqual(log_site1.id, response.data['results'][1]['id'])
