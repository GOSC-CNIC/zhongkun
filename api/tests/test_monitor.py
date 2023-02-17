import time
from urllib import parse

from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache as django_cache

from monitor.tests import (
    get_or_create_monitor_job_ceph, get_or_create_monitor_job_server, get_or_create_monitor_job_meeting,
    get_or_create_monitor_provider
)
from monitor.models import (
    MonitorJobCeph, MonitorProvider, MonitorJobServer, MonitorOrganization,
    MonitorWebsite, MonitorWebsiteTask, MonitorWebsiteVersionProvider, get_str_hash
)
from monitor.managers import (
    CephQueryChoices, ServerQueryChoices, VideoMeetingQueryChoices, WebsiteQueryChoices
)
from utils.test import get_or_create_user, get_test_case_settings
from . import set_auth_header, MyAPITestCase


class MonitorCephTests(MyAPITestCase):
    def setUp(self):
        self.user = None
        set_auth_header(self)

    def query_response(self, monitor_unit_id: str = None, query_tag: str = None):
        querys = {}
        if monitor_unit_id:
            querys['monitor_unit_id'] = monitor_unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('api:monitor-ceph-query-list')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, monitor_unit_id: str, query_tag: str):
        response = self.query_response(monitor_unit_id=monitor_unit_id, query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["value", "monitor"], data_item)
        if data_item["value"] is not None:
            self.assertIsInstance(data_item["value"], list)
            self.assertEqual(len(data_item["value"]), 2)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], data_item["monitor"])

        return response

    def test_query(self):
        monitor_job_ceph = get_or_create_monitor_job_ceph()
        ceph_unit_id = monitor_job_ceph.id

        # no permission
        response = self.query_response(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        monitor_job_ceph.users.add(self.user)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_BYTES.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_IN.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_OUT.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_UP.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_DOWN.value)

        # no permission
        monitor_job_ceph.users.remove(self.user)
        response = self.query_response(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_BYTES.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_IN.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_OUT.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_UP.value)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_DOWN.value)

    def query_range_response(self, monitor_unit_id: str = None, query_tag: str = None,
                             start: int = None, end: int = None, step: int = None):
        querys = {}
        if monitor_unit_id:
            querys['monitor_unit_id'] = monitor_unit_id

        if query_tag:
            querys['query'] = query_tag

        if start:
            querys['start'] = start

        if end:
            querys['end'] = end

        if query_tag:
            querys['step'] = step

        url = reverse('api:monitor-ceph-query-range')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_range_ok_test(self, monitor_unit_id: str, query_tag: str, start: int, end: int, step: int):
        values_len = (end - start) // step + 1
        response = self.query_range_response(monitor_unit_id=monitor_unit_id, query_tag=query_tag,
                                             start=start, end=end, step=step)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["values", "monitor"], data_item)
        self.assertIsInstance(data_item["values"], list)
        self.assertEqual(len(data_item["values"]), values_len)
        if data_item["values"]:
            self.assertEqual(len(data_item["values"][0]), 2)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], data_item["monitor"])

        return response

    def test_query_range(self):
        monitor_job_ceph = get_or_create_monitor_job_ceph()
        ceph_unit_id = monitor_job_ceph.id

        # query parameter test
        end = int(time.time())
        start = end - 600
        step = 300

        # param "start"
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start='bad', end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=-1, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "end"
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=start, end='bad', step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=start, end=-1, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "step"
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=start, end=end, step=-1)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=start, end=end, step=0)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "end" >= "start" required
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=end + 1, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # 每个时间序列11000点的最大分辨率
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=start - 12000, end=end, step=1)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        end = int(time.time())
        start = end - 600
        step = 300

        # no permission
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=start, end=end, step=step)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        monitor_job_ceph.users.add(self.user)
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=end, end=start, step=step)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_BYTES.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value,
            start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_IN.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_OUT.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_UP.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_DOWN.value,
                                 start=start, end=end, step=step)

        # no permission
        monitor_job_ceph.users.remove(self.user)
        response = self.query_range_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
            start=start, end=end, step=step)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_BYTES.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value,
            start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_IN.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_OUT.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_UP.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_DOWN.value,
                                 start=start, end=end, step=step)


class MonitorServerTests(MyAPITestCase):
    def setUp(self):
        self.user = None
        set_auth_header(self)

    def query_response(self, monitor_unit_id: str = None, query_tag: str = None):
        querys = {}
        if monitor_unit_id:
            querys['monitor_unit_id'] = monitor_unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('api:monitor-server-query-list')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, monitor_unit_id: str, query_tag: str):
        response = self.query_response(monitor_unit_id=monitor_unit_id, query_tag=query_tag)
        if response.status_code != 200:
            print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["value", "monitor"], data_item)
        if data_item["value"] is not None:
            self.assertIsInstance(data_item["value"], list)
            self.assertEqual(len(data_item["value"]), 2)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], data_item["monitor"])

        return response

    def test_query(self):
        monitor_server_unit = get_or_create_monitor_job_server()
        server_unit_id = monitor_server_unit.id

        # no permission
        response = self.query_response(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.CPU_USAGE.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        monitor_server_unit.users.add(self.user)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HOST_COUNT.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HOST_UP_COUNT.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.CPU_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MEM_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.DISK_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MIN_CPU_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MAX_CPU_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MIN_MEM_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MAX_MEM_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MIN_DISK_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MAX_DISK_USAGE.value)

        # no permission
        monitor_server_unit.users.remove(self.user)
        response = self.query_response(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.CPU_USAGE.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HOST_COUNT.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HOST_UP_COUNT.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.CPU_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MEM_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.DISK_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MIN_CPU_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MAX_CPU_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MIN_MEM_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MAX_MEM_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MIN_DISK_USAGE.value)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.MAX_DISK_USAGE.value)


class MonitorVideoMeetingTests(MyAPITestCase):
    def setUp(self):
        self.user = None
        set_auth_header(self)

    def query_response(self, query_tag: str = None):
        querys = {}
        if query_tag:
            querys['query'] = query_tag

        url = reverse('api:monitor-video-meeting-query-list')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, query_tag: str):
        response = self.query_response(query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["value", "monitor"], data_item)
        self.assertKeysIn(["name", "name_en", "job_tag"], data_item["monitor"])
        self.assertIsInstance(data_item["value"], list)
        values = data_item["value"]
        self.assertKeysIn(['value', 'metric'], values[0])
        self.assertKeysIn(['name', 'longitude', 'latitude', 'ipv4s'], values[0]['metric'])
        self.assertIsInstance(values[0]['metric']["ipv4s"], list)
        return response

    def test_query(self):
        get_or_create_monitor_job_meeting()

        # no permission
        # response = self.query_response(query_tag=VideoMeetingQueryChoices.NODE_STATUS.value)
        # self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        # self.user.set_federal_admin()
        self.query_ok_test(query_tag=VideoMeetingQueryChoices.NODE_STATUS.value)
        self.query_ok_test(query_tag=VideoMeetingQueryChoices.NODE_LATENCY.value)


class MonitorUnitCephTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')

    def test_list_unit(self):
        provider = MonitorProvider()
        provider.save(force_insert=True)
        org = MonitorOrganization(
            name='test', name_en='test en', abbreviation='t', modification=timezone.now()
        )
        org.save(force_insert=True)
        unit_ceph1 = MonitorJobCeph(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            provider=provider, organization=org
        )
        unit_ceph1.save(force_insert=True)

        unit_ceph2 = MonitorJobCeph(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
            provider=provider, organization=org
        )
        unit_ceph2.save(force_insert=True)

        unit_ceph3 = MonitorJobCeph(
            name='name3', name_en='name_en3', job_tag='job_tag3', sort_weight=3,
            provider=provider
        )
        unit_ceph3.save(force_insert=True)

        unit_ceph4 = MonitorJobCeph(
            name='name4', name_en='name_en4', job_tag='job_tag4',  sort_weight=8,
            provider=provider
        )
        unit_ceph4.save(force_insert=True)

        # 未认证
        url = reverse('api:monitor-unit-ceph-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # 没有管理权限
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # unit_ceph4
        unit_ceph4.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(['id', "name", "name_en", "job_tag", 'creation', 'remark',
                           'sort_weight', 'grafana_url', 'dashboard_url', 'organization'], response.data['results'][0])
        self.assertEqual(unit_ceph4.id, response.data['results'][0]['id'])
        self.assertIsNone(response.data['results'][0]['organization'])

        # unit_ceph1, unit_ceph4
        unit_ceph1.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_ceph1.id, response.data['results'][0]['id'])
        self.assertKeysIn(['id', "name", "name_en", "abbreviation", 'creation', 'sort_weight'
                           ], response.data['results'][0]['organization'])

        # unit_ceph1, unit_ceph4, unit_ceph2
        unit_ceph2.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(unit_ceph1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_ceph4.id, response.data['results'][1]['id'])
        self.assertEqual(unit_ceph2.id, response.data['results'][2]['id'])

        # query "organization_id"
        query = parse.urlencode(query={'organization_id': org.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_ceph1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_ceph2.id, response.data['results'][1]['id'])

        # page_size
        query = parse.urlencode(query={'page': 1, 'page_size': 2})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_ceph1.id, response.data['results'][0]['id'])

        # federal_admin
        self.user.set_federal_admin()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(unit_ceph1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_ceph4.id, response.data['results'][1]['id'])
        self.assertEqual(unit_ceph2.id, response.data['results'][2]['id'])
        self.assertEqual(unit_ceph3.id, response.data['results'][3]['id'])

        # query "organization_id"
        query = parse.urlencode(query={'organization_id': org.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_ceph1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_ceph2.id, response.data['results'][1]['id'])


class MonitorUnitServerTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')

    def test_list_server_unit(self):
        provider = MonitorProvider()
        provider.save(force_insert=True)

        unit_server1 = MonitorJobServer(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            provider=provider
        )
        unit_server1.save(force_insert=True)

        unit_server2 = MonitorJobServer(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
            provider=provider
        )
        unit_server2.save(force_insert=True)

        unit_server3 = MonitorJobServer(
            name='name3', name_en='name_en3', job_tag='job_tag3', sort_weight=3,
            provider=provider
        )
        unit_server3.save(force_insert=True)

        unit_server4 = MonitorJobServer(
            name='name4', name_en='name_en4', job_tag='job_tag4',  sort_weight=8,
            provider=provider
        )
        unit_server4.save(force_insert=True)

        # 未认证
        url = reverse('api:monitor-unit-server-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # 没有管理权限
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # unit_server4
        unit_server4.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(['id', "name", "name_en", "job_tag", 'creation', 'remark',
                           'sort_weight', 'grafana_url', 'dashboard_url'], response.data['results'][0])
        self.assertEqual(unit_server4.id, response.data['results'][0]['id'])

        # unit_server1, unit_server4
        unit_server1.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])

        # unit_server1, unit_server4, unit_server2
        unit_server2.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_server4.id, response.data['results'][1]['id'])
        self.assertEqual(unit_server2.id, response.data['results'][2]['id'])

        # page_size
        query = parse.urlencode(query={'page': 1, 'page_size': 2})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])

        # federal_admin
        self.user.set_federal_admin()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_server4.id, response.data['results'][1]['id'])
        self.assertEqual(unit_server2.id, response.data['results'][2]['id'])
        self.assertEqual(unit_server3.id, response.data['results'][3]['id'])


class MonitorWebsiteTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.user2 = get_or_create_user(username='tom@cnic.cn', password='password')

    def test_create_website_task(self):
        # NotAuthenticated
        url = reverse('api:monitor-website-list')
        r = self.client.post(path=url, data={
            'name': 'name-test', 'url': 'https://test.c', 'remark': 'test'
        }, content_type='application/json')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # InvalidUrl
        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'url': 'https://test.c', 'remark': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUrl', response=r)

        # user, 1 ok
        self.client.force_login(self.user)
        website_url = 'https://test.cn'
        r = self.client.post(path=url, data={
            'name': 'name-test', 'url': website_url, 'remark': 'test'
        })
        self.assertKeysIn(keys=['id', 'name', 'url', 'remark', 'url_hash', 'creation'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name-test', 'url': website_url,
            'remark': 'test', 'url_hash': get_str_hash(website_url)
        }, d=r.data)

        website_id = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 1)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id)
        self.assertEqual(website.name, 'name-test')
        self.assertEqual(website.url, website_url)
        self.assertEqual(website.remark, 'test')

        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 1)

        # user, 2 ok
        website_url2 = 'https://test66.com'
        r = self.client.post(path=url, data={
            'name': 'name-test666', 'url': website_url2, 'remark': '测试t88'
        })
        self.assertKeysIn(keys=['id', 'name', 'url', 'remark', 'url_hash', 'creation'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name-test666', 'url': website_url2,
            'remark': '测试t88', 'url_hash': get_str_hash(website_url2)
        }, d=r.data)

        website_id2 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 2)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id2)
        self.assertEqual(website.name, 'name-test666')
        self.assertEqual(website.url, website_url2)
        self.assertEqual(website.remark, '测试t88')

        self.assertEqual(MonitorWebsiteTask.objects.count(), 2)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url2)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 2)

        # user2, 1 ok
        self.client.logout()
        self.client.force_login(self.user2)
        website_url3 = 'https://test3.cnn'
        r = self.client.post(path=url, data={
            'name': 'name3-test', 'url': website_url3, 'remark': '3test'
        })
        self.assertKeysIn(keys=['id', 'name', 'url', 'remark', 'url_hash', 'creation'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name3-test', 'url': website_url3,
            'remark': '3test', 'url_hash': get_str_hash(website_url3)
        }, d=r.data)

        website_id3 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id3)
        self.assertEqual(website.name, 'name3-test')
        self.assertEqual(website.url, website_url3)
        self.assertEqual(website.remark, '3test')

        self.assertEqual(MonitorWebsiteTask.objects.count(), 3)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url3)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 3)

        # user2, TargetAlreadyExists
        r = self.client.post(path=url, data={
            'name': 'name4-test', 'url': website_url3, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=r)

        # user2, 2 ok, url == website_url2
        r = self.client.post(path=url, data={
            'name': 'name4-test', 'url': website_url2, 'remark': '4test'
        })
        self.assertKeysIn(keys=['id', 'name', 'url', 'remark', 'url_hash', 'creation'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name4-test', 'url': website_url2,
            'remark': '4test', 'url_hash': get_str_hash(website_url2)
        }, d=r.data)

        website_id4 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 4)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id4)
        self.assertEqual(website.name, 'name4-test')
        self.assertEqual(website.url, website_url2)
        self.assertEqual(website.remark, '4test')

        self.assertEqual(MonitorWebsiteTask.objects.count(), 3)
        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 3)

    def test_list_website_task(self):
        # NotAuthenticated
        base_url = reverse('api:monitor-website-list')
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # ok, no data
        self.client.force_login(self.user)
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(r.data['page_num'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 0)

        # add data
        nt = timezone.now()
        user_website1 = MonitorWebsite(
            name='name1', url='https://11.com', remark='remark1', user_id=self.user.id,
            creation=nt, modification=nt
        )
        user_website1.save(force_insert=True)

        nt = timezone.now()
        user_website2 = MonitorWebsite(
            name='name2', url='https://222.com', remark='remark2', user_id=self.user.id,
            creation=nt, modification=nt
        )
        user_website2.save(force_insert=True)

        nt = timezone.now()
        user2_website1 = MonitorWebsite(
            name='name3', url='https://333.com', remark='remark3', user_id=self.user2.id,
            creation=nt, modification=nt
        )
        user2_website1.save(force_insert=True)

        nt = timezone.now()
        user_website6 = MonitorWebsite(
            name='name66', url='https://666.com', remark='remark66', user_id=self.user.id,
            creation=nt, modification=nt
        )
        user_website6.save(force_insert=True)

        # ok, list
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_num'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 3)
        self.assertKeysIn(keys=[
            'id', 'name', 'url', 'remark', 'url_hash', 'creation', 'user'
        ], container=r.data['results'][0])
        self.assert_is_subdict_of(sub={
            'name': user_website6.name, 'url': user_website6.url,
            'remark': user_website6.remark, 'url_hash': user_website6.url_hash
        }, d=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][0]['user']['username'], self.user.username)

        # ok, list, page_size
        query = parse.urlencode(query={'page_size': 2})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], user_website6.id)
        self.assertEqual(r.data['results'][1]['id'], user_website2.id)

        # ok, list, page, page_size
        query = parse.urlencode(query={'page': 2, 'page_size': 2})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(r.data['page_size'], 2)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], user_website1.id)

    def test_delete_website_task(self):
        # NotAuthenticated
        url = reverse('api:monitor-website-detail', kwargs={'id': 'test'})
        r = self.client.delete(path=url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # add data
        nt = timezone.now()
        website_url1 = 'https://11.com'
        user_website1 = MonitorWebsite(
            name='name1', url=website_url1, remark='remark1', user_id=self.user.id,
            creation=nt, modification=nt
        )
        user_website1.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=website_url1)
        task1.save(force_insert=True)

        nt = timezone.now()
        website_url2 = 'https://222.com'
        user_website2 = MonitorWebsite(
            name='name2', url=website_url2, remark='remark2', user_id=self.user.id,
            creation=nt, modification=nt
        )
        user_website2.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=website_url2)
        task1.save(force_insert=True)

        nt = timezone.now()
        user2_website2 = MonitorWebsite(
            name='name22', url=website_url2, remark='remark22', user_id=self.user2.id,
            creation=nt, modification=nt
        )
        user2_website2.save(force_insert=True)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 0)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        self.assertEqual(MonitorWebsiteTask.objects.count(), 2)

        # ok, NotFound
        self.client.force_login(self.user)
        r = self.client.delete(path=url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # AccessDenied, user delete user2's website
        url = reverse('api:monitor-website-detail', kwargs={'id': user2_website2.id})
        r = self.client.delete(path=url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user delete website1 ok
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website1.id})
        r = self.client.delete(path=url)
        self.assertEqual(r.status_code, 204)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 1)
        self.assertEqual(MonitorWebsite.objects.count(), 2)
        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)

        # user delete website2 ok
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website2.id})
        r = self.client.delete(path=url)
        self.assertEqual(r.status_code, 204)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 1)
        self.assertEqual(MonitorWebsite.objects.count(), 1)
        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)
        task = MonitorWebsiteTask.objects.first()
        self.assertEqual(task.url, user2_website2.url)

    def test_task_version_list(self):
        url = reverse('api:monitor-website-task-version')
        r = self.client.get(path=url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['version'], 0)

        v = MonitorWebsiteVersionProvider.get_instance()
        v.version = 66
        v.save(update_fields=['version'])

        r = self.client.get(path=url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['version'], 66)

        task1 = MonitorWebsiteTask(url='https://11.com')
        task1.save(force_insert=True)
        task2 = MonitorWebsiteTask(url='https://22.com')
        task2.save(force_insert=True)
        task3 = MonitorWebsiteTask(url='https://33.com')
        task3.save(force_insert=True)
        task4 = MonitorWebsiteTask(url='https://44.com')
        task4.save(force_insert=True)

        # list task
        base_url = reverse('api:monitor-website-task-list')
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'has_next', 'page_size', 'marker', 'next_marker', 'results'
        ], container=r.data)
        self.assertEqual(r.data['has_next'], False)
        self.assertEqual(r.data['page_size'], 2000)
        self.assertIsNone(r.data['marker'])
        self.assertIsNone(r.data['next_marker'])
        self.assertEqual(len(r.data['results']), 4)
        self.assertKeysIn(keys=['url', 'url_hash', 'creation'], container=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['url'], task4.url)

        # list task, query "page_size"
        query = parse.urlencode(query={'page_size': 2})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['has_next'], True)
        self.assertEqual(r.data['page_size'], 2)
        self.assertIsNone(r.data['marker'])
        self.assertIsNotNone(r.data['next_marker'])
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['url'], task4.url)
        next_marker = r.data['next_marker']

        # list task, query "page_size" and "marker"
        query = parse.urlencode(query={'page_size': 2, 'marker': next_marker})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['has_next'], False)
        self.assertEqual(r.data['page_size'], 2)
        self.assertEqual(r.data['marker'], next_marker)
        self.assertIsNone(r.data['next_marker'])
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['url'], task2.url)

    def test_change_website_task(self):
        # NotAuthenticated
        url = reverse('api:monitor-website-detail', kwargs={'id': 'test'})
        r = self.client.put(path=url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # add data
        nt = timezone.now()
        website_url1 = 'https://111.com'
        user_website1 = MonitorWebsite(
            name='name1', url=website_url1, remark='remark1', user_id=self.user.id,
            creation=nt, modification=nt
        )
        user_website1.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=website_url1)
        task1.save(force_insert=True)

        nt = timezone.now()
        website_url2 = 'https://2222.com'
        user_website2 = MonitorWebsite(
            name='name2', url=website_url2, remark='remark2', user_id=self.user.id,
            creation=nt, modification=nt
        )
        user_website2.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=website_url2)
        task1.save(force_insert=True)

        nt = timezone.now()
        user2_website2 = MonitorWebsite(
            name='name222', url=website_url2, remark='remark222', user_id=self.user2.id,
            creation=nt, modification=nt
        )
        user2_website2.save(force_insert=True)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 0)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].url, website_url2)
        self.assertEqual(tasks[1].url, website_url1)

        # ok, NotFound
        self.client.force_login(self.user)
        url = reverse('api:monitor-website-detail', kwargs={'id': 'test'})

        # no "name"， BadRequest
        r = self.client.put(path=url, data={'url': 'https://ccc.com', 'remark': ''})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        # InvalidUrl
        r = self.client.put(path=url, data={'name': 'nametest', 'url': 'https://ccc', 'remark': ''})
        self.assertErrorResponse(status_code=400, code='InvalidUrl', response=r)

        # NotFound
        data = {'name': 'test', 'url': 'https://ccc.com', 'remark': ''}
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # AccessDenied, user change user2's website
        url = reverse('api:monitor-website-detail', kwargs={'id': user2_website2.id})
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user change website1 name, ok
        data = {'name': 'change name', 'url': user_website1.url, 'remark': user_website1.remark}
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website1 = MonitorWebsite.objects.get(id=user_website1.id)
        self.assertEqual(website1.name, 'change name')
        self.assertEqual(website1.url, user_website1.url)
        self.assertEqual(website1.remark, user_website1.remark)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 0)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].url, website_url2)
        self.assertEqual(tasks[1].url, website_url1)

        # user change website1 "name" and "url", ok
        new_website_url1 = 'https://666.cn'
        data = {'name': user_website1.name, 'url': new_website_url1, 'remark': user_website1.remark}
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website1 = MonitorWebsite.objects.get(id=user_website1.id)
        self.assertEqual(website1.name, user_website1.name)
        self.assertEqual(website1.url, new_website_url1)
        self.assertEqual(website1.remark, user_website1.remark)

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 1)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[1].url, website_url2)
        self.assertEqual(tasks[0].url, new_website_url1)

        # user change website2 "remark" and "url", ok
        new_website_url2 = 'https://888.cn'
        data = {'name': user_website2.name, 'url': new_website_url2, 'remark': '新的 remark'}
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website2.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website2 = MonitorWebsite.objects.get(id=user_website2.id)
        self.assertEqual(website2.name, user_website2.name)
        self.assertEqual(website2.url, new_website_url2)
        self.assertEqual(website2.remark, '新的 remark')

        version = MonitorWebsiteVersionProvider.get_instance()
        self.assertEqual(version.version, 2)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].url, new_website_url2)
        self.assertEqual(tasks[1].url, new_website_url1)
        self.assertEqual(tasks[2].url, website_url2)


class MonitorWebsiteQueryTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.user2 = get_or_create_user(username='tom@cnic.cn', password='password')
        self.provider = get_or_create_monitor_provider(alias='MONITOR_WEBSITE')
        testcase_settings = get_test_case_settings()
        nt = timezone.now()
        self.website = MonitorWebsite(
            name='test', url=testcase_settings['MONITOR_WEBSITE']['WEBSITE_URL'], remark='', user=self.user,
            creation=nt, modification=nt
        )
        self.website.save(force_insert=True)

    def test_query(self):
        website = self.website
        # NotAuthenticated
        r = self.query_response(website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # InvalidArgument
        r = self.query_response(website_id=website.id, query_tag='InvalidArgument')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # 清除 可能的 provider 缓存
        django_cache.delete('monitor_website_provider')

        # Conflict, not set provider
        r = self.query_response(website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # NotFound
        r = self.query_response(website_id='websiteid', query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # set provider
        ins = MonitorWebsiteVersionProvider.get_instance()
        ins.provider_id = self.provider.id
        ins.save(update_fields=['provider_id'])

        # ok
        self.query_ok_test(website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.query_ok_test(website_id=website.id, query_tag=WebsiteQueryChoices.DURATION_SECONDS.value)

        # NotFound
        self.client.logout()
        self.client.force_login(self.user2)
        r = self.query_response(website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

    def query_response(self, website_id: str, query_tag: str):
        url = reverse('api:monitor-website-data-query', kwargs={'id': website_id})
        query = parse.urlencode(query={'query': query_tag})
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, website_id: str, query_tag: str):
        response = self.query_response(website_id=website_id, query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["values", "metric"], data_item)
        self.assertEqual(self.website.url, data_item['metric']['url'])
        self.assertIsInstance(data_item["values"], list)
        if data_item["values"]:
            self.assertEqual(len(data_item["values"][0]), 2)

        return response

    def test_query_range(self):
        # query parameter test
        end = int(time.time())
        start = end - 600
        step = 300

        website = self.website
        # NotAuthenticated
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step
        )
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # BadRequest, param "start"
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            end=end, step=step
        )
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start='bad', end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=-1, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # param "end"
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end='bad', step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=-1, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "step"
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=-1)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=0)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "end" >= "start" required
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=end + 1, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # 每个时间序列10000点的最大分辨率
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start - 11000, end=end, step=1)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # InvalidArgument
        r = self.query_range_response(
            website_id=website.id, query_tag='InvalidArgument', start=start, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # NotFound
        r = self.query_range_response(
            website_id='websiteid', query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step
        )
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # 清楚 可能的 provider 缓存
        django_cache.delete('monitor_website_provider')

        # Conflict, not set provider
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step
        )
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # set provider
        ins = MonitorWebsiteVersionProvider.get_instance()
        ins.provider_id = self.provider.id
        ins.save(update_fields=['provider_id'])

        # ok
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step
        )
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.DURATION_SECONDS.value,
            start=start, end=end, step=step
        )

        # NotFound
        self.client.logout()
        self.client.force_login(self.user2)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step
        )
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

    def query_range_response(
            self, website_id: str, query_tag: str, start: int = None, end: int = None, step: int = None
    ):
        querys = {}
        if query_tag:
            querys['query'] = query_tag

        if start:
            querys['start'] = start

        if end:
            querys['end'] = end

        if query_tag:
            querys['step'] = step

        url = reverse('api:monitor-website-data-query-range', kwargs={'id': website_id})
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_range_ok_test(self, website_id: str, query_tag: str, start: int, end: int, step: int):
        values_len = (end - start) // step + 1
        response = self.query_range_response(
            website_id=website_id, query_tag=query_tag, start=start, end=end, step=step)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["values", "metric"], data_item)
        self.assertEqual(self.website.url, data_item['metric']['url'])
        self.assertIsInstance(data_item["values"], list)
        self.assertEqual(len(data_item["values"]), values_len)
        if data_item["values"]:
            self.assertEqual(len(data_item["values"][0]), 2)

        return response


class MonitorOrganizationTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn', password='password')

    def test_list(self):
        base_url = reverse('api:monitor-organization-list')
        # NotAuthenticated
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # ok, 0
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 0)

        # add data
        org1 = MonitorOrganization(
            name='测试test1', name_en='test英文1', abbreviation='test1', sort_weight=66, modification=timezone.now()
        )
        org1.save(force_insert=True)
        org2 = MonitorOrganization(
            name='测试test2', name_en='test英文2', abbreviation='test2', sort_weight=88, modification=timezone.now()
        )
        org2.save(force_insert=True)
        org3 = MonitorOrganization(
            name='测试test3', name_en='test英文3', abbreviation='test3', sort_weight=68, modification=timezone.now()
        )
        org3.save(force_insert=True)

        # ok, 3
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 3)
        self.assertKeysIn(keys=[
            "id", "name", "name_en", "abbreviation", "sort_weight", "creation", "country", "city",
            "postal_code", "address", "longitude", "latitude", "modification", "remark"
        ], container=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['id'], org2.id)
        self.assertEqual(r.data['results'][1]['id'], org3.id)
        self.assertEqual(r.data['results'][2]['id'], org1.id)

        # ok, "page", "page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        r = self.client.get(path=f"{base_url}?{query}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(r.data['page_size'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], org3.id)

        query = parse.urlencode(query={'page': 1, 'page_size': 2})
        r = self.client.get(path=f"{base_url}?{query}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 2)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], org2.id)
        self.assertEqual(r.data['results'][1]['id'], org3.id)
