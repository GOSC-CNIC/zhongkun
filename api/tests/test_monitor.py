import time
from urllib import parse

from django.urls import reverse

from monitor.tests import (
    get_or_create_monitor_job_ceph, get_or_create_monitor_job_server, get_or_create_monitor_job_meeting
)
from monitor.models import MonitorJobCeph, MonitorProvider, MonitorJobServer
from utils.test import get_or_create_user
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
        from monitor.managers import CephQueryChoices

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
        from monitor.managers import CephQueryChoices

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
        from monitor.managers import ServerQueryChoices

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
        from monitor.managers import VideoMeetingQueryChoices

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

        unit_ceph1 = MonitorJobCeph(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            provider=provider
        )
        unit_ceph1.save(force_insert=True)

        unit_ceph2 = MonitorJobCeph(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
            provider=provider
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
                           'sort_weight', 'grafana_url', 'dashboard_url'], response.data['results'][0])
        self.assertEqual(unit_ceph4.id, response.data['results'][0]['id'])

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
