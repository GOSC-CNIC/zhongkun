from urllib import parse

from django.urls import reverse
from django.utils import timezone

from monitor.models import (
    LogSite, LogSiteType
)
from utils.test import get_or_create_user, MyAPITestCase, get_or_create_org_data_center
from scripts.workers.req_logs import LogSiteReqCounter
from .tests import get_or_create_job_log_site


class LogSiteTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')

    def test_list_unit(self):
        odc = get_or_create_org_data_center()

        site_type1 = LogSiteType(name='obj', name_en='obj en', sort_weight=6)
        site_type1.save(force_insert=True)
        log_site1 = LogSite(
            name='name1', name_en='name_en1', log_type=LogSite.LogType.HTTP.value,
            site_type_id=None, job_tag='job_tag1', sort_weight=10,
        )
        log_site1.save(force_insert=True)

        log_site2 = LogSite(
            name='name2', name_en='name_en2', log_type=LogSite.LogType.HTTP.value,
            site_type_id=site_type1.id, job_tag='job_tag2', sort_weight=5,
            org_data_center=odc
        )
        log_site2.save(force_insert=True)
        log_site3 = LogSite(
            name='name3', name_en='name_en3', log_type=LogSite.LogType.NAT.value,
            site_type_id=site_type1.id, job_tag='job_tag3', sort_weight=3,
            org_data_center=odc
        )
        log_site3.save(force_insert=True)

        log_site4 = LogSite(
            name='name4', name_en='name_en4', log_type=LogSite.LogType.NAT.value,
            site_type_id=site_type1.id, job_tag='job_tag4', sort_weight=8,
            org_data_center=odc
        )
        log_site4.save(force_insert=True)

        # 未认证
        url = reverse('monitor-api:log-site-list')
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
                           'sort_weight', 'org_data_center'], response.data['results'][0])
        self.assertEqual(log_site4.id, response.data['results'][0]['id'])
        self.assertKeysIn([
            'id', "name", "name_en", 'organization', 'sort_weight'], response.data['results'][0]['org_data_center'])
        self.assertKeysIn([
            'id', "name", "name_en", 'sort_weight'], response.data['results'][0]['org_data_center']['organization'])
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
        self.assertIsNone(response.data['results'][1]['org_data_center'])
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

        # test org data center admin
        log_site1.users.remove(self.user)
        log_site2.users.remove(self.user)
        log_site4.users.remove(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        odc.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(log_site3.id, response.data['results'][0]['id'])
        self.assertEqual(log_site2.id, response.data['results'][1]['id'])
        self.assertEqual(log_site4.id, response.data['results'][2]['id'])

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

    def test_log_site_query(self):
        log_site = get_or_create_job_log_site()
        # 未认证
        url = reverse('monitor-api:log-site-query')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user)

        # InvalidStart
        query = parse.urlencode(query={'log_site_id': 'xxx'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidStart', response=response)

        query = parse.urlencode(query={'log_site_id': 'xxx', 'start': '12345678'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidStart', response=response)

        # InvalidEnd
        timestamp = int(timezone.now().timestamp())
        query = parse.urlencode(query={'log_site_id': 'xxx', 'start': timestamp})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidEnd', response=response)

        query = parse.urlencode(query={'log_site_id': 'xxx', 'start': timestamp, 'end': '12345678'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidEnd', response=response)

        # InvalidDirection
        query = parse.urlencode(query={'log_site_id': 'xxx', 'start': timestamp, 'end': timestamp, 'direction': 'ccc'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidDirection', response=response)

        # InvalidLimit
        query = parse.urlencode(query={
            'log_site_id': 'xxx', 'start': timestamp, 'end': timestamp, 'direction': 'forward', 'limit': 'xx'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidLimit', response=response)

        query = parse.urlencode(query={
            'log_site_id': 'xxx', 'start': timestamp, 'end': timestamp, 'direction': 'backward', 'limit': '-1'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidLimit', response=response)

        # log site id
        query = parse.urlencode(query={
            'start': timestamp, 'end': timestamp, 'direction': 'backward', 'limit': '10',
        })
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidSiteId', response=response)

        query = parse.urlencode(query={
            'log_site_id': 'xxx', 'start': timestamp, 'end': timestamp, 'direction': 'backward', 'limit': '10',
            'search': 'tes`t'
        })
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidSearch', response=response)

        query = parse.urlencode(query={
            'log_site_id': 'xxx', 'start': timestamp, 'end': timestamp, 'direction': 'backward', 'limit': '10',
        })
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # 没有管理权限
        query = parse.urlencode(query={
            'log_site_id': log_site.id, 'start': timestamp, 'end': timestamp, 'direction': 'backward', 'limit': '10'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # log_site4
        log_site.users.add(self.user)
        query = parse.urlencode(query={
            'log_site_id': log_site.id, 'start': timestamp-1000, 'end': timestamp, 'direction': 'backward',
            'limit': '10'
        })
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        if response.data:
            item = response.data[0]
            self.assertKeysIn(["stream", "values"], item)
            self.assertEqual(len(item['values']), 10)
            self.assertEqual(len(item['values'][0]), 2)

        # search
        query = parse.urlencode(query={
            'log_site_id': log_site.id, 'start': timestamp - 1000, 'end': timestamp, 'direction': 'backward',
            'limit': '10', 'search': 'dadadadaqdq'
        })
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 0)

        # --- test org data center admin ---
        # 没有管理权限
        log_site.users.remove(self.user)
        query = parse.urlencode(query={
            'log_site_id': log_site.id, 'start': timestamp, 'end': timestamp, 'direction': 'backward', 'limit': '10'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        log_site.org_data_center.users.add(self.user)
        query = parse.urlencode(query={
            'log_site_id': log_site.id, 'start': timestamp - 1000, 'end': timestamp, 'direction': 'backward',
            'limit': '10'
        })
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        if response.data:
            item = response.data[0]
            self.assertKeysIn(["stream", "values"], item)
            self.assertEqual(len(item['values']), 10)
            self.assertEqual(len(item['values'][0]), 2)

    def test_list_time_count(self):
        now_timestamp = int(timezone.now().replace(second=0).timestamp())
        log_site = get_or_create_job_log_site()
        # 未认证
        url = reverse('monitor-api:log-site-time-count')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user)

        # InvalidStart
        query = parse.urlencode(query={'log_site_id': 'xxx', 'end': now_timestamp})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidStart', response=response)

        # InvalidStart
        query = parse.urlencode(query={'log_site_id': 'xxx', 'start': now_timestamp})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidEnd', response=response)

        # AccessDenied
        query = parse.urlencode(query={'log_site_id': log_site.id, 'start': now_timestamp, 'end': now_timestamp + 100})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # TargetNotExist
        query = parse.urlencode(query={'log_site_id': 'xxx', 'start': now_timestamp, 'end': now_timestamp + 100})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # ok
        log_site.users.add(self.user)
        query = parse.urlencode(query={'log_site_id': log_site.id, 'start': now_timestamp-2, 'end': now_timestamp + 100})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        LogSiteReqCounter().run()
        # url有缓存，url不能和上面完全一样
        query = parse.urlencode(query={'log_site_id': log_site.id, 'start': now_timestamp, 'end': now_timestamp + 100})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(["count", "id", "timestamp", 'site_id'], response.data['results'][0])
