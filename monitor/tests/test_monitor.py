import time
from decimal import Decimal
from datetime import timedelta
from urllib import parse

from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache as django_cache
from django.conf import settings

from service.models import DataCenter
from monitor.models import (
    MonitorJobCeph, MonitorProvider, MonitorJobServer, WebsiteDetectionPoint,
    MonitorWebsite, MonitorWebsiteRecord, MonitorWebsiteTask, MonitorWebsiteVersion, get_str_hash
)
from monitor.managers import (
    CephQueryChoices, ServerQueryChoices, VideoMeetingQueryChoices, WebsiteQueryChoices,
    MonitorWebsiteManager
)
from bill.models import PayApp, PayAppService
from order.models import Price
from utils.test import (
    get_or_create_user, get_test_case_settings, get_or_create_service, get_or_create_organization,
    MyAPITestCase
)

from .tests import (
    get_or_create_monitor_job_ceph, get_or_create_monitor_job_server, get_or_create_monitor_job_meeting,
    get_or_create_monitor_provider
)
from ..handlers.monitor_website import TaskSchemeType


class MonitorCephTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.client.force_login(user=self.user)
        self.service1 = get_or_create_service()

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

        # 关联云主机服务单元
        monitor_job_ceph.service_id = self.service1.id
        monitor_job_ceph.save(update_fields=['service_id'])

        # no permission
        response = self.query_response(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 服务单元管理员权限测试
        self.service1.users.add(self.user)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        # 移除服务单元管理员权限
        self.service1.users.remove(self.user)

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

        # all together
        response = self.query_response(
            monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = CephQueryChoices.values
        tags.remove(CephQueryChoices.ALL_TOGETHER.value)
        for tag in tags:
            self.assertIn(tag, response.data)
            tag_data = response.data[tag]
            self.assertIsInstance(tag_data, list)
            if tag_data:
                data_item = tag_data[0]
                self.assertKeysIn(["metric", "value", "monitor"], data_item)
                if data_item["value"] is not None:
                    self.assertIsInstance(data_item["value"], list)
                    self.assertEqual(len(data_item["value"]), 2)
                self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], data_item["monitor"])

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
        self.user = get_or_create_user(password='password')
        self.client.force_login(user=self.user)
        self.service1 = get_or_create_service()

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

        # 关联云主机服务单元
        monitor_server_unit.service_id = self.service1.id
        monitor_server_unit.save(update_fields=['service_id'])

        # no permission
        response = self.query_response(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 服务单元管理员权限测试
        self.service1.users.add(self.user)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)
        # 移除服务单元管理员权限
        self.service1.users.remove(self.user)

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

        # all together
        response = self.query_response(
            monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = ServerQueryChoices.values
        tags.remove(ServerQueryChoices.ALL_TOGETHER.value)
        for tag in tags:
            self.assertIn(tag, response.data)
            tag_data = response.data[tag]
            self.assertIsInstance(tag_data, list)
            if tag_data:
                data_item = tag_data[0]
                self.assertKeysIn(["value", "monitor"], data_item)
                if data_item["value"] is not None:
                    self.assertIsInstance(data_item["value"], list)
                    self.assertEqual(len(data_item["value"]), 2)
                self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], data_item["monitor"])


class MonitorVideoMeetingTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.client.force_login(user=self.user)

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
        self.service1 = get_or_create_service()

    def test_list_unit(self):
        provider = MonitorProvider()
        provider.save(force_insert=True)
        org = DataCenter(
            name='test', name_en='test en', abbreviation='t', creation_time=timezone.now()
        )
        org.save(force_insert=True)
        unit_ceph1 = MonitorJobCeph(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            provider=provider, organization=org
        )
        unit_ceph1.save(force_insert=True)

        unit_ceph2 = MonitorJobCeph(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
            provider=provider, organization=org, service_id=self.service1.id
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
        self.assertKeysIn(['id', "name", "name_en", "abbreviation", 'creation_time', 'sort_weight'
                           ], response.data['results'][0]['organization'])

        # unit_ceph1, unit_ceph4, unit_ceph2
        unit_ceph2.service.users.add(self.user)     # 关联的云主机服务单元管理员
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
        self.service1 = get_or_create_service()

    def test_list_server_unit(self):
        provider = MonitorProvider()
        provider.save(force_insert=True)
        org = DataCenter(
            name='test', name_en='test en', abbreviation='t', creation_time=timezone.now()
        )
        org.save(force_insert=True)

        unit_server1 = MonitorJobServer(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            provider=provider, organization=org
        )
        unit_server1.save(force_insert=True)

        unit_server2 = MonitorJobServer(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
            provider=provider, organization=org, service_id=self.service1.id
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
        self.assertIsNone(response.data['results'][0]['organization'])

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
        self.assertKeysIn(['id', "name", "name_en", "abbreviation", 'creation_time', 'sort_weight'
                           ], response.data['results'][0]['organization'])

        # unit_server1, unit_server4, unit_server2
        unit_server2.service.users.add(self.user)   # 关联的云主机服务单元管理员权限
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

        # query "organization_id"
        query = parse.urlencode(query={'organization_id': org.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_server2.id, response.data['results'][1]['id'])

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

        # query "organization_id"
        query = parse.urlencode(query={'organization_id': org.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_server2.id, response.data['results'][1]['id'])


class MonitorWebsiteTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.user2 = get_or_create_user(username='tom@cnic.cn', password='password')

    def test_create_website_task(self):
        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        app = app
        po = get_or_create_organization(name='机构')
        po.save()
        app_service1 = PayAppService(
            name='website monitor', app=app, orgnazition=po
        )
        app_service1.save()

        price = Price(
            vm_ram=Decimal('0.0'),
            vm_cpu=Decimal('0.0'),
            vm_disk=Decimal('0'),
            vm_pub_ip=Decimal('0'),
            vm_upstream=Decimal('0'),
            vm_downstream=Decimal('1'),
            vm_disk_snap=Decimal('0'),
            disk_size=Decimal('1.02'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            prepaid_discount=66,
            mntr_site_base=Decimal('0.3'),
            mntr_site_tamper=Decimal('0.2'),
            mntr_site_security=Decimal('0.5')
        )
        price.save()

        # NotAuthenticated
        url = reverse('api:monitor-website-list')
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.c', 'uri': '/', 'remark': 'test'
        }, content_type='application/json')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # InvalidUrl
        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.c', 'uri': '/', 'remark': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUrl', response=r)

        # InvalidUri
        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.com', 'uri': '', 'remark': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.com', 'uri': 'a/b/c', 'remark': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True, 'remark': 'test'
        })
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=r)
        site_version_ins = MonitorWebsiteVersion.get_instance()
        site_version_ins.pay_app_service_id = app_service1.id
        site_version_ins.save(update_fields=['pay_app_service_id'])

        # balance 100
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True, 'remark': 'test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        userpointaccount = self.user.userpointaccount
        userpointaccount.balance = Decimal('99')
        userpointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True, 'remark': 'test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        userpointaccount.balance = Decimal('100')
        userpointaccount.save(update_fields=['balance'])

        # user, 1 ok
        website_url = 'https://test.cn/a/b?test=1&c=6#test'
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True, 'remark': 'test'
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name-test', 'url': website_url,
            'remark': 'test', 'url_hash': get_str_hash(website_url),
            'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True
        }, d=r.data)

        website_id = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 1)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id)
        self.assertEqual(website.name, 'name-test')
        self.assertEqual(website.scheme, 'https://')
        self.assertEqual(website.hostname, 'test.cn')
        self.assertEqual(website.uri, '/a/b?test=1&c=6#test')
        self.assertIs(website.is_tamper_resistant, True)
        self.assertEqual(website.url, website_url)
        self.assertEqual(website.remark, 'test')

        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url)
        self.assertEqual(task.url_hash, website.url_hash)
        self.assertIs(task.is_tamper_resistant, True)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 1)

        # user, 2 ok
        website_url2 = 'https://test66.com/'
        r = self.client.post(path=url, data={
            'name': 'name-test666', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/', 'remark': '测试t88'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        userpointaccount.balance = Decimal('103')
        userpointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name-test666', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/', 'remark': '测试t88'
        })
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)
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
        self.assertEqual(website.scheme, 'https://')
        self.assertEqual(website.hostname, 'test66.com')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, False)

        self.assertEqual(MonitorWebsiteTask.objects.count(), 2)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url2)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, False)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 2)

        # user2, 1 ok
        self.client.logout()
        self.client.force_login(self.user2)

        # balance 100
        website_url3 = 'https://test3.cnn/'
        r = self.client.post(path=url, data={
            'name': 'name3-test', 'scheme': 'https://', 'hostname': 'test3.cnn', 'uri': '/', 'remark': '3test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        user2pointaccount = self.user2.userpointaccount
        user2pointaccount.balance = Decimal('99')
        user2pointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name3-test', 'scheme': 'https://', 'hostname': 'test3.cnn', 'uri': '/', 'remark': '3test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        user2pointaccount.balance = Decimal('100')
        user2pointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name3-test', 'scheme': 'https://', 'hostname': 'test3.cnn', 'uri': '/', 'remark': '3test'
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)
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
        self.assertEqual(website.scheme, 'https://')
        self.assertEqual(website.hostname, 'test3.cnn')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, False)

        self.assertEqual(MonitorWebsiteTask.objects.count(), 3)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url3)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, False)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 3)

        # user2, TargetAlreadyExists; website_url3='https://test3.cnn'
        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'https://', 'hostname': 'test3.cnn', 'uri': '/',
            'is_tamper_resistant': True, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=r)

        # user2, 2 ok, website_url2 = 'https://test66.com/'
        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/',
            'is_tamper_resistant': True, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        user2pointaccount.balance = Decimal('100.3')
        user2pointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/',
            'is_tamper_resistant': True, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        user2pointaccount.balance = Decimal('100.5')
        user2pointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/',
            'is_tamper_resistant': True, 'remark': '4test'
        })
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)
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
        self.assertEqual(website.scheme, 'https://')
        self.assertEqual(website.hostname, 'test66.com')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, True)

        self.assertEqual(MonitorWebsiteTask.objects.count(), 3)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation')[1]
        self.assertEqual(task.url, website_url2)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, True)
        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 4)

        # tcp test
        user2pointaccount.balance = Decimal('130')
        user2pointaccount.save(update_fields=['balance'])
        website_tcp1 = 'tcp://testtcp.com:22/'
        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com', 'uri': '/a/b.txt', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com', 'uri': '', 'remark': 'test tcp'
        })

        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:', 'uri': '/a/b.txt', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:22', 'uri': '/a/b.txt', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:220000', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:test', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp:sss.com:test', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:22', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)

        self.assert_is_subdict_of(sub={
            'name': 'tcp1-test', 'url': website_tcp1,
            'remark': 'test tcp', 'url_hash': get_str_hash(website_tcp1)
        }, d=r.data)

        website_tcpid5 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 5)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_tcpid5)
        self.assertEqual(website.name, 'tcp1-test')
        self.assertEqual(website.url, website_tcp1)
        self.assertEqual(website.remark, 'test tcp')
        self.assertEqual(website.scheme, 'tcp://')
        self.assertEqual(website.hostname, 'testtcp.com:22')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, False)

        self.assertEqual(MonitorWebsiteTask.objects.count(), 4)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_tcp1)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, False)
        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 5)

        # user2, TargetAlreadyExists; website_tcp1='tcp://testtcp.com:22'
        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:22', 'uri': '/',
            'is_tamper_resistant': False, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=r)

        website_tcp2 = 'tcp://111.111.111.111:22/'
        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': '111.111.111.111:22', 'uri': '/a/b.txt',
            'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp2-test', 'scheme': 'tcp://', 'hostname': '111.111.111.111:22', 'uri': '/',
            'remark': 'test tcp2', 'is_tamper_resistant': True
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp2-test', 'scheme': 'tcp://', 'hostname': '111.111.111.111:22', 'uri': '/',
            'remark': 'test tcp2', 'is_tamper_resistant': False
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)

        self.assert_is_subdict_of(sub={
            'name': 'tcp2-test', 'url': website_tcp2,
            'remark': 'test tcp2', 'url_hash': get_str_hash(website_tcp2)
        }, d=r.data)

        website_tcpid6 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 6)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_tcpid6)
        self.assertEqual(website.name, 'tcp2-test')
        self.assertEqual(website.url, website_tcp2)
        self.assertEqual(website.remark, 'test tcp2')
        self.assertEqual(website.scheme, 'tcp://')
        self.assertEqual(website.hostname, '111.111.111.111:22')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, False)   # tcp不支持

        self.assertEqual(MonitorWebsiteTask.objects.count(), 5)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_tcp2)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, False)
        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 6)

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
        user_tcp_task1 = MonitorWebsite(
            name='tcp_task1', scheme='tcp://', hostname='2222.com:8888', uri='/', is_tamper_resistant=False,
            remark='remark tcp_task1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_tcp_task1.save(force_insert=True)

        nt = timezone.now()
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='11.com', uri='/', is_tamper_resistant=True,
            remark='remark1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website1.url = user_website1.full_url
        user_website1.save(force_insert=True)

        nt = timezone.now()
        user_website2 = MonitorWebsite(
            name='name2', scheme='https://', hostname='222.com', uri='/', is_tamper_resistant=False,
            remark='remark2', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website2.url = user_website2.full_url
        user_website2.save(force_insert=True)

        nt = timezone.now()
        user2_website1 = MonitorWebsite(
            name='name3', scheme='https://', hostname='333.com', uri='/', is_tamper_resistant=True,
            remark='remark3', user_id=self.user2.id, creation=nt, modification=nt
        )
        user2_website1.url = user2_website1.full_url
        user2_website1.save(force_insert=True)

        nt = timezone.now()
        user_website6 = MonitorWebsite(
            name='name66', scheme='https://', hostname='666.com', uri='/a/b?a=6&c=6#test', is_tamper_resistant=False,
            remark='remark66', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website6.url = user_website6.full_url
        user_website6.save(force_insert=True)

        # ok, list
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(r.data['page_num'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 4)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'user', 'modification', 'is_attention'
        ], container=r.data['results'][0])
        self.assert_is_subdict_of(sub={
            'name': user_website6.name, 'url': user_website6.url,
            'remark': user_website6.remark, 'url_hash': user_website6.url_hash,
            'scheme': 'https://', 'hostname': '666.com', 'uri': '/a/b?a=6&c=6#test',
            'is_tamper_resistant': False
        }, d=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][0]['user']['username'], self.user.username)

        # ok, list, page_size
        query = parse.urlencode(query={'page_size': 2})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 4)
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
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(r.data['page_size'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], user_website1.id)
        self.assertEqual(r.data['results'][1]['id'], user_tcp_task1.id)

        # ok, list, scheme
        query = parse.urlencode(query={'scheme': TaskSchemeType.TCP.value})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], user_tcp_task1.id)

    def test_delete_website_task(self):
        # NotAuthenticated
        url = reverse('api:monitor-website-detail', kwargs={'id': 'test'})
        r = self.client.delete(path=url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # add data
        nt = timezone.now()
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='11.com', uri='/', is_tamper_resistant=False,
            remark='remark1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website1.url = user_website1.full_url
        user_website1.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=user_website1.full_url, is_tamper_resistant=True)
        task1.save(force_insert=True)

        nt = timezone.now()
        website_url2 = 'https://222.com/'
        user_website2 = MonitorWebsite(
            name='name2',  scheme='https://', hostname='222.com', uri='/', is_tamper_resistant=True,
            url=website_url2, remark='remark2', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website2.url = user_website2.full_url
        user_website2.save(force_insert=True)
        task2 = MonitorWebsiteTask(url=user_website2.full_url, is_tamper_resistant=True)
        task2.save(force_insert=True)

        nt = timezone.now()
        user2_website2 = MonitorWebsite(
            name='name22', scheme='https://', hostname='222.com', uri='/', is_tamper_resistant=False,
            remark='remark22', user_id=self.user2.id, creation=nt, modification=nt
        )
        user2_website2.url = user2_website2.full_url
        user2_website2.save(force_insert=True)

        version = MonitorWebsiteVersion.get_instance()
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

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 1)
        self.assertEqual(MonitorWebsite.objects.count(), 2)
        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)
        self.assertEqual(MonitorWebsiteRecord.objects.count(), 1)
        record1: MonitorWebsiteRecord = MonitorWebsiteRecord.objects.first()
        self.assertEqual(user_website1.full_url, record1.full_url)
        self.assertEqual(user_website1.creation, record1.creation)
        self.assertEqual(record1.type, MonitorWebsiteRecord.RecordType.DELETED.value)

        # user delete website2 ok
        task2.refresh_from_db()
        self.assertIs(task2.is_tamper_resistant, True)
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website2.id})
        r = self.client.delete(path=url)
        self.assertEqual(r.status_code, 204)
        task2.refresh_from_db()
        self.assertIs(task2.is_tamper_resistant, False)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 2)
        self.assertEqual(MonitorWebsite.objects.count(), 1)
        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)
        task = MonitorWebsiteTask.objects.first()
        self.assertEqual(task.url, user2_website2.url)
        self.assertEqual(MonitorWebsiteRecord.objects.count(), 2)

    def test_task_version_list(self):
        url = reverse('api:monitor-website-task-version')
        r = self.client.get(path=url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['version'], 0)

        v = MonitorWebsiteVersion.get_instance()
        v.version = 66
        v.save(update_fields=['version'])

        r = self.client.get(path=url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['version'], 66)

        task1 = MonitorWebsiteTask(url='https://11.com/', is_tamper_resistant=True)
        task1.save(force_insert=True)
        task2 = MonitorWebsiteTask(url='https://22.com/', is_tamper_resistant=True)
        task2.save(force_insert=True)
        task3 = MonitorWebsiteTask(url='https://33.com/', is_tamper_resistant=False)
        task3.save(force_insert=True)
        task4 = MonitorWebsiteTask(url='https://44.com/', is_tamper_resistant=False)
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
        self.assertKeysIn(keys=['url', 'url_hash', 'creation', 'is_tamper_resistant'], container=r.data['results'][0])
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
        website_url1 = 'https://111.com/'
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='111.com', uri='/', is_tamper_resistant=False,
            remark='remark1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website1.url = user_website1.full_url
        user_website1.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=user_website1.full_url, is_tamper_resistant=False)
        task1.save(force_insert=True)

        nt = timezone.now()
        website_url2 = 'https://2222.com/'
        user_website2 = MonitorWebsite(
            name='name2', scheme='https://', hostname='2222.com', uri='/', is_tamper_resistant=True,
            remark='remark2', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website2.url = user_website2.full_url
        user_website2.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=user_website2.full_url, is_tamper_resistant=True)
        task1.save(force_insert=True)

        nt = timezone.now()
        user2_website2 = MonitorWebsite(
            name='name222', scheme='https://', hostname='2222.com', uri='/', is_tamper_resistant=False,
            remark='remark222', user_id=self.user2.id, creation=nt, modification=nt
        )
        user2_website2.url = user2_website2.full_url
        user2_website2.save(force_insert=True)

        version = MonitorWebsiteVersion.get_instance()
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
        r = self.client.put(path=url, data={
            'scheme': 'https://', 'hostname': 'ccc.com', 'uri': '/', 'is_tamper_resistant': True, 'remark': ''})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        # NotFound
        data = {'name': 'test', 'scheme': 'https://', 'hostname': 'ccc.com', 'uri': '/',
                'is_tamper_resistant': True, 'remark': ''}
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # AccessDenied, user change user2's website
        url = reverse('api:monitor-website-detail', kwargs={'id': user2_website2.id})
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user change website1 name, ok
        data = {'name': 'change name', 'scheme': user_website1.scheme, 'hostname': user_website1.hostname,
                'uri': user_website1.uri, 'is_tamper_resistant': user_website1.is_tamper_resistant,
                'remark': user_website1.remark}
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website1 = MonitorWebsite.objects.get(id=user_website1.id)
        self.assertEqual(website1.name, 'change name')
        self.assertEqual(website1.url, user_website1.url)
        self.assertEqual(website1.remark, user_website1.remark)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 0)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].url, website_url2)
        self.assertIs(tasks[0].is_tamper_resistant, True)
        self.assertEqual(tasks[1].url, website_url1)
        self.assertIs(tasks[1].is_tamper_resistant, False)

        # user change website1 "name" and "url", InvalidUrl
        r = self.client.put(path=url, data={
            'name': 'nametest', 'scheme': 'https://', 'hostname': 'ccc', 'uri': '/', 'remark': ''})
        self.assertErrorResponse(status_code=400, code='InvalidUrl', response=r)

        # user change website1 "name" and "url", ok
        new_website_url1 = 'https://666.cn/'
        data = {'name': user_website1.name, 'scheme': 'https://', 'hostname': '666.cn', 'uri': '/',
                'remark': user_website1.remark}
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website1 = MonitorWebsite.objects.get(id=user_website1.id)
        self.assertEqual(website1.name, user_website1.name)
        self.assertEqual(website1.url, new_website_url1)
        self.assertEqual(website1.remark, user_website1.remark)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'url', 'is_tamper_resistant',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'
        ], container=r.data)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 1)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[1].url, website_url2)
        self.assertIs(tasks[1].is_tamper_resistant, True)
        self.assertEqual(tasks[0].url, new_website_url1)
        self.assertIs(tasks[0].is_tamper_resistant, False)

        # user change website2 "remark" and "uri", ok
        new_website_url2 = 'https://888.cn/a/?b=6&c=8#test'
        data = {'name': user_website2.name, 'scheme': 'https://', 'hostname': '888.cn', 'uri': '/a/?b=6&c=8#test',
                'remark': '新的 remark'}
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website2.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website2 = MonitorWebsite.objects.get(id=user_website2.id)
        self.assertEqual(website2.name, user_website2.name)
        self.assertEqual(website2.url, new_website_url2)
        self.assertEqual(website2.remark, '新的 remark')
        self.assertIs(website2.is_tamper_resistant, True)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 2)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].url, new_website_url2)
        self.assertIs(tasks[0].is_tamper_resistant, True)
        self.assertEqual(tasks[1].url, new_website_url1)
        self.assertIs(tasks[1].is_tamper_resistant, False)
        self.assertEqual(tasks[2].url, website_url2)
        self.assertIs(tasks[2].is_tamper_resistant, False)

        # user change website2 "is_tamper_resistant", ok
        data = {'name': user_website2.name, 'scheme': 'https://', 'hostname': '888.cn', 'uri': '/a/?b=6&c=8#test',
                'is_tamper_resistant': False, 'url': new_website_url2, 'remark': '新的 remark'}
        url = reverse('api:monitor-website-detail', kwargs={'id': user_website2.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website2 = MonitorWebsite.objects.get(id=user_website2.id)
        self.assertEqual(website2.name, user_website2.name)
        self.assertEqual(website2.url, new_website_url2)
        self.assertEqual(website2.remark, '新的 remark')
        self.assertIs(website2.is_tamper_resistant, False)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 3)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].url, new_website_url2)
        self.assertIs(tasks[0].is_tamper_resistant, False)
        self.assertEqual(tasks[1].url, new_website_url1)
        self.assertIs(tasks[1].is_tamper_resistant, False)
        self.assertEqual(tasks[2].url, website_url2)
        self.assertIs(tasks[2].is_tamper_resistant, False)

        # tcp test
        nt = timezone.now()
        user1_tcp_task1 = MonitorWebsite(
            name='tcp_task1', scheme='tcp://', hostname='2222.com:8888', uri='/', is_tamper_resistant=False,
            remark='remark tcp_task1', user_id=self.user.id, creation=nt, modification=nt
        )
        user1_tcp_task1.save(force_insert=True)

        data = {'name': user1_tcp_task1.name, 'scheme': 'tcp://', 'hostname': '2222.com:8888', 'uri': '/',
                'is_tamper_resistant': True, 'remark': '新的 remark'}
        url = reverse('api:monitor-website-detail', kwargs={'id': user1_tcp_task1.id})
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        data = {'name': user1_tcp_task1.name, 'scheme': 'tcp://', 'hostname': '2222.com', 'uri': '/',
                'remark': '新的 remark'}
        url = reverse('api:monitor-website-detail', kwargs={'id': user1_tcp_task1.id})
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        data = {'name': user1_tcp_task1.name, 'scheme': 'tcp://', 'hostname': '2222.cn:666', 'uri': '/',
                'remark': '新的 remark'}
        url = reverse('api:monitor-website-detail', kwargs={'id': user1_tcp_task1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        user1_tcp_task1.refresh_from_db()
        self.assertEqual(user1_tcp_task1.hostname, '2222.cn:666')

        data = {'name': user1_tcp_task1.name, 'scheme': 'https://', 'hostname': '2222.cn:666', 'uri': '/',
                'remark': '新的 remark'}
        url = reverse('api:monitor-website-detail', kwargs={'id': user1_tcp_task1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)

    def test_list_website_detection_point(self):
        # NotAuthenticated
        base_url = reverse('api:monitor-website-detection-point')
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
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en2', creation=nt, modification=nt, remark='remark2', enable=False
        )
        detection_point2.save(force_insert=True)

        # ok, list
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_num'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 2)

        # ok, list, page_size
        query = parse.urlencode(query={'page_size': 1})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], detection_point2.id)

        # ok, list, page, page_size
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(r.data['page_size'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], detection_point1.id)

        # query "enable" true
        query = parse.urlencode(query={'enable': True})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], detection_point1.id)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'remark', 'modification', 'creation', 'enable'
        ], container=r.data['results'][0])

        # query "enable" false
        query = parse.urlencode(query={'enable': False})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], detection_point2.id)

    def test_website_task_attention_mark(self):
        # NotAuthenticated
        url = reverse('api:monitor-website-mark-attention', kwargs={'id': 'test'})
        r = self.client.post(path=url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # add data
        nt = timezone.now()
        website_url1 = 'https://111.com'
        user_website1 = MonitorWebsite(
            name='name1', url=website_url1, remark='remark1', user_id=self.user.id,
            creation=nt, modification=nt, is_attention=False
        )
        user_website1.save(force_insert=True)

        self.client.force_login(self.user2)

        # query "action"
        url = reverse('api:monitor-website-mark-attention', kwargs={'id': 'test'})
        r = self.client.post(path=url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'action': ''})
        r = self.client.post(path=f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'action': 'marttt'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # NotFound
        url = reverse('api:monitor-website-mark-attention', kwargs={'id': 'test'})
        query = parse.urlencode(query={'action': 'mark'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # AccessDenied, user2 change user's website
        url = reverse('api:monitor-website-mark-attention', kwargs={'id': user_website1.id})
        query = parse.urlencode(query={'action': 'mark'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.client.logout()
        self.client.force_login(self.user)

        # user2 mark website1, ok
        url = reverse('api:monitor-website-mark-attention', kwargs={'id': user_website1.id})
        query = parse.urlencode(query={'action': 'mark'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'url', 'remark', 'url_hash', 'creation', 'modification', 'is_attention'
        ], container=r.data)

        user_website1.refresh_from_db()
        self.assertIs(user_website1.is_attention, True)

        # user2 unmark website1, ok
        url = reverse('api:monitor-website-mark-attention', kwargs={'id': user_website1.id})
        query = parse.urlencode(query={'action': 'unMark'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'url', 'remark', 'url_hash', 'creation', 'modification', 'is_attention'
        ], container=r.data)

        user_website1.refresh_from_db()
        self.assertIs(user_website1.is_attention, False)

    def test_list_site_emails(self):
        settings.API_EMAIL_ALLOWED_IPS = []
        base_url = reverse('api:monitor-website-user-email')
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        query = parse.urlencode(query={'url_hash': ''})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'url_hash': 'xxxx'})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.client.force_login(self.user)
        r = self.client.get(reverse('api:email-realip'))
        real_ip = r.data['real_ip']
        settings.API_EMAIL_ALLOWED_IPS = [real_ip]
        self.client.logout()

        # ok, no data
        url_hash = 'xxxx'
        query = parse.urlencode(query={'url_hash': url_hash})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['url_hash', 'results'], container=r.data)
        self.assertEqual(r.data['url_hash'], url_hash)
        self.assertEqual(len(r.data['results']), 0)

        # add data
        user3 = get_or_create_user(username='lisi@qq.com')
        nt = timezone.now()
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='111.com', uri='/', is_tamper_resistant=True,
            remark='remark1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website1.url = user_website1.full_url
        user_website1.save(force_insert=True)

        nt = timezone.now()
        user2_website1 = MonitorWebsite(
            name='name2', scheme='https://', hostname='111.com', uri='/', is_tamper_resistant=False,
            remark='remark2', user_id=self.user2.id, creation=nt, modification=nt
        )
        user2_website1.save(force_insert=True)

        nt = timezone.now()
        user3_website3 = MonitorWebsite(
            name='name3', scheme='https://', hostname='333.com', uri='/', is_tamper_resistant=True,
            remark='remark3', user_id=user3.id, creation=nt, modification=nt
        )
        user3_website3.url = user3_website3.full_url
        user3_website3.save(force_insert=True)

        # ok, list
        url_hash = user_website1.url_hash
        query = parse.urlencode(query={'url_hash': url_hash})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['url_hash', 'results'], container=r.data)
        self.assertEqual(r.data['url_hash'], url_hash)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'scheme', 'hostname', 'uri', 'email'
        ], container=r.data['results'][0])
        for item in r.data['results']:
            url1 = item['scheme'] + item['hostname'] + item['uri']
            self.assertEqual(url1, user2_website1.full_url)
            self.assertIn(item['email'], [self.user.username, self.user2.username])


class MonitorWebsiteQueryTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.user2 = get_or_create_user(username='tom@cnic.cn', password='password')
        self.provider = get_or_create_monitor_provider(alias='MONITOR_WEBSITE')
        testcase_settings = get_test_case_settings()
        nt = timezone.now()
        self.website = MonitorWebsite(
            name='test',
            scheme=testcase_settings['MONITOR_WEBSITE']['WEBSITE_SCHEME'],
            hostname=testcase_settings['MONITOR_WEBSITE']['WEBSITE_HOSTNAME'],
            uri=testcase_settings['MONITOR_WEBSITE']['WEBSITE_URI'],
            url=testcase_settings['MONITOR_WEBSITE']['WEBSITE_URL'],
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        self.website.save(force_insert=True)

    def test_query(self):
        website = self.website

        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en1', creation=nt, modification=nt,
            remark='remark1', enable=False, provider=self.provider
        )
        detection_point2.save(force_insert=True)

        # NotAuthenticated
        r = self.query_response(
            website_id=website.id, detection_point_id='',
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # InvalidArgument
        r = self.query_response(
            website_id=website.id, detection_point_id='detection_point_id',
            query_tag='InvalidArgument')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)

        # Conflict, not set provider
        r = self.query_response(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # set provider
        detection_point1.provider_id = self.provider.id
        detection_point1.save(update_fields=['provider_id'])

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)

        # NotFound
        r = self.query_response(
            website_id='websiteid', detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # NoSuchDetectionPoint
        r = self.query_response(
            website_id=website.id, detection_point_id='detection_point1.id',
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=404, code='NoSuchDetectionPoint', response=r)

        # Conflict, detection_point2 not enable
        r = self.query_response(
            website_id=website.id, detection_point_id=detection_point2.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ok
        self.query_ok_test(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.query_ok_test(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.SUCCESS.value)
        self.query_ok_test(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value)
        self.query_ok_test(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_DURATION_SECONDS.value, list_len=5)

        # tcp
        nt = timezone.now()
        tcp_task = MonitorWebsite(
            name='test',
            scheme='tcp://',
            hostname='127.0.0.1:8888',
            uri='/',
            url='',
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        tcp_task.save(force_insert=True)

        # InvalidArgument
        r = self.query_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_DURATION_SECONDS.value)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        r = self.query_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        r = self.query_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.SUCCESS.value)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])
        r = self.query_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

        # NotFound
        self.client.logout()
        self.client.force_login(self.user2)
        r = self.query_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

    def query_response(self, website_id: str, query_tag: str, detection_point_id: str):
        url = reverse('api:monitor-website-data-query', kwargs={'id': website_id})
        query = parse.urlencode(query={'query': query_tag, 'detection_point_id': detection_point_id})
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, website_id: str, query_tag: str, detection_point_id: str, list_len=1):
        response = self.query_response(
            website_id=website_id, query_tag=query_tag, detection_point_id=detection_point_id)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), list_len)
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
        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en1', creation=nt, modification=nt,
            remark='remark1', enable=False, provider=self.provider
        )
        detection_point2.save(force_insert=True)

        # NotAuthenticated
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # BadRequest, param "start"
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start='bad', end=end, step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=-1, end=end, step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # param "end"
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end='bad', step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=-1, step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "step"
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=-1, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=0, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "end" >= "start" required
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=end + 1, end=end, step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # 每个时间序列10000点的最大分辨率
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start - 11000, end=end, step=1, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # InvalidArgument
        r = self.query_range_response(
            website_id=website.id, query_tag='InvalidArgument', start=start, end=end, step=step,
            detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # NotFound
        r = self.query_range_response(
            website_id='websiteid', query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)

        # Conflict, not set provider
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # set provider
        detection_point1.provider_id = self.provider.id
        detection_point1.save(update_fields=['provider_id'])

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)

        # NoSuchDetectionPoint
        r = self.query_range_response(
            website_id=website.id, detection_point_id='detection_point1.id',
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=404, code='NoSuchDetectionPoint', response=r)

        # Conflict, detection_point2 not enable
        r = self.query_range_response(
            website_id=website.id, detection_point_id=detection_point2.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ok
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.SUCCESS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.DURATION_SECONDS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_DURATION_SECONDS.value,
            start=start, end=end, step=step, list_len=5, detection_point_id=detection_point1.id
        )

        # tcp
        nt = timezone.now()
        tcp_task = MonitorWebsite(
            name='test',
            scheme='tcp://',
            hostname='127.0.0.1:8888',
            uri='/',
            url='',
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        tcp_task.save(force_insert=True)

        # InvalidArgument
        r = self.query_range_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        r = self.query_range_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_DURATION_SECONDS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        r = self.query_range_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.SUCCESS.value, start=start, end=end, step=step)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])
        r = self.query_range_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value, start=start, end=end, step=step)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

        # NotFound
        self.client.logout()
        self.client.force_login(self.user2)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

    def query_range_response(
            self, website_id: str, detection_point_id: str,
            query_tag: str, start: int = None, end: int = None, step: int = None,
    ):
        querys = {'detection_point_id': detection_point_id}
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

    def query_range_ok_test(
            self, website_id: str, detection_point_id: str,
            query_tag: str, start: int, end: int, step: int, list_len=1
    ):
        values_len = (end - start) // step + 1
        response = self.query_range_response(
            website_id=website_id, detection_point_id=detection_point_id,
            query_tag=query_tag, start=start, end=end, step=step)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), list_len)
        data_item = response.data[0]
        self.assertKeysIn(["values", "metric"], data_item)
        self.assertEqual(self.website.url, data_item['metric']['url'])
        self.assertIsInstance(data_item["values"], list)
        self.assertEqual(len(data_item["values"]), values_len)
        if data_item["values"]:
            self.assertEqual(len(data_item["values"][0]), 2)

        return response

    def duration_query_response(self, start: int, end: int, detection_point_id: str):
        url = reverse('api:monitor-website-duration-distribution')
        querys = {}
        if start:
            querys['start'] = start

        if end:
            querys['end'] = end

        if detection_point_id:
            querys['detection_point_id'] = detection_point_id

        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def test_duration_distribution(self):
        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True,
            provider=self.provider
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en1', creation=nt, modification=nt,
            remark='remark1', enable=False, provider=self.provider
        )
        detection_point2.save(force_insert=True)

        tcp_task = MonitorWebsite(
            name='test',
            scheme='tcp://',
            hostname='127.0.0.1',
            uri='/',
            url='',
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        tcp_task.save(force_insert=True)

        # NotAuthenticated
        day_ago = nt - timedelta(days=1)
        start = int(day_ago.timestamp())
        end = int(nt.timestamp())
        r = self.duration_query_response(start=start, end=end, detection_point_id='')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)
        # NoSuchDetectionPoint
        r = self.duration_query_response(start=start, end=end, detection_point_id='notfound')
        self.assertErrorResponse(status_code=404, code='NoSuchDetectionPoint', response=r)

        # Conflict, detection_point2 not enable
        r = self.duration_query_response(start=start, end=end, detection_point_id=detection_point2.id)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ok
        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)
        r = self.duration_query_response(start=start, end=end, detection_point_id='')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 2)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)
        r = self.duration_query_response(start=start, end=end, detection_point_id=detection_point1.id)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)

    def _status_query_response(self, detection_point_id: str):
        url = reverse('api:monitor-website-status-overview')
        querys = {}
        if detection_point_id:
            querys['detection_point_id'] = detection_point_id

        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def test_status_overview(self):
        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True,
            provider=self.provider
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en1', creation=nt, modification=nt,
            remark='remark1', enable=False, provider=self.provider
        )
        detection_point2.save(force_insert=True)

        tcp_task = MonitorWebsite(
            name='test',
            scheme='tcp://',
            hostname='127.0.0.1',
            uri='/',
            url='',
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        tcp_task.save(force_insert=True)

        # NotAuthenticated
        r = self._status_query_response(detection_point_id='')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # NoSuchDetectionPoint
        r = self._status_query_response(detection_point_id='notfound')
        self.assertErrorResponse(status_code=404, code='NoSuchDetectionPoint', response=r)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)
        # Conflict, detection_point2 not enable
        r = self._status_query_response(detection_point_id=detection_point2.id)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ok
        r = self._status_query_response(detection_point_id='')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['total', 'invalid', 'valid'], r.data)
        self.assertEqual(r.data['total'], 1)
        self.assertEqual(r.data['invalid'] + r.data['valid'], 1)

        r = self._status_query_response(detection_point_id=detection_point1.id)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['total', 'invalid', 'valid'], r.data)
        self.assertEqual(r.data['total'], 1)
        self.assertEqual(r.data['invalid'] + r.data['valid'], 1)
