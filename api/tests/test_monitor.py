import time
from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_service
from monitor.tests import (
    get_or_create_monitor_job_ceph, get_or_create_monitor_job_server, get_or_create_monitor_job_meeting
)

from . import set_auth_header, MyAPITestCase


class MonitorCephTests(MyAPITestCase):
    def setUp(self):
        self.user = None
        set_auth_header(self)
        self.service = get_or_create_service()

    def query_response(self, service_id: str = None, query_tag: str = None):
        querys = {}
        if service_id:
            querys['service_id'] = service_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('api:monitor-ceph-query-list')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, service_id: str, query_tag: str):
        response = self.query_response(service_id=service_id, query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["value", "monitor"], data_item)
        if data_item["value"] is not None:
            self.assertIsInstance(data_item["value"], list)
            self.assertEqual(len(data_item["value"]), 2)
        self.assertKeysIn(["name", "name_en", "job_tag", "service_id", "creation"], data_item["monitor"])

        return response

    def test_query(self):
        from monitor.managers import CephQueryChoices

        service_id = self.service.id
        monitor_job_ceph = get_or_create_monitor_job_ceph(service_id=service_id)

        # no permission
        response = self.query_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        self.service.users.add(self.user)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_BYTES.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_IN.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_OUT.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_UP.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_DOWN.value)

        # no permission
        self.service.users.remove(self.user)
        response = self.query_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_BYTES.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_IN.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_OUT.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_UP.value)
        self.query_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_DOWN.value)

    def query_range_response(self, service_id: str = None, query_tag: str = None,
                             start: int = None, end: int = None, step: int = None):
        querys = {}
        if service_id:
            querys['service_id'] = service_id

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

    def query_range_ok_test(self, service_id: str, query_tag: str, start: int, end: int, step: int):
        values_len = (end - start) // step + 1
        response = self.query_range_response(service_id=service_id, query_tag=query_tag,
                                             start=start, end=end, step=step)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["values", "monitor"], data_item)
        self.assertIsInstance(data_item["values"], list)
        self.assertEqual(len(data_item["values"]), values_len)
        if data_item["values"]:
            self.assertEqual(len(data_item["values"][0]), 2)
        self.assertKeysIn(["name", "name_en", "job_tag", "service_id", "creation"], data_item["monitor"])

        return response

    def test_query_range(self):
        from monitor.managers import CephQueryChoices

        service_id = self.service.id
        monitor_job_ceph = get_or_create_monitor_job_ceph(service_id=service_id)

        # query parameter test
        end = int(time.time())
        start = end - 600
        step = 300

        # param "start"
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             end=end, step=step)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start='bad', end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=-1, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "end"
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=start, end='bad', step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=start, end=-1, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "step"
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=start, end=end, step=-1)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=start, end=end, step=0)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "end" >= "start" required
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=end + 1, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # 每个时间序列11000点的最大分辨率
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=start - 12000, end=end, step=1)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        end = int(time.time())
        start = end - 600
        step = 300

        # no permission
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=start, end=end, step=step)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        self.service.users.add(self.user)
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=end, end=start, step=step)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_BYTES.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_IN.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_OUT.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_UP.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_DOWN.value,
                                 start=start, end=end, step=step)

        # no permission
        self.service.users.remove(self.user)
        response = self.query_range_response(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                             start=start, end=end, step=step)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_BYTES.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_IN.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_OUT.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_UP.value,
                                 start=start, end=end, step=step)
        self.query_range_ok_test(service_id=service_id, query_tag=CephQueryChoices.OSD_DOWN.value,
                                 start=start, end=end, step=step)


class MonitorServerTests(MyAPITestCase):
    def setUp(self):
        self.user = None
        set_auth_header(self)
        self.service = get_or_create_service()

    def query_response(self, service_id: str = None, query_tag: str = None):
        querys = {}
        if service_id:
            querys['service_id'] = service_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('api:monitor-server-query-list')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, service_id: str, query_tag: str):
        response = self.query_response(service_id=service_id, query_tag=query_tag)
        if response.status_code != 200:
            print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["value", "monitor"], data_item)
        if data_item["value"] is not None:
            self.assertIsInstance(data_item["value"], list)
            self.assertEqual(len(data_item["value"]), 2)
        self.assertKeysIn(["name", "name_en", "job_tag", "service_id", "creation"], data_item["monitor"])

        return response

    def test_query(self):
        from monitor.managers import ServerQueryChoices

        service_id = self.service.id
        get_or_create_monitor_job_server(service_id=service_id)

        # no permission
        response = self.query_response(service_id=service_id, query_tag=ServerQueryChoices.CPU_USAGE.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        self.service.users.add(self.user)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.HOST_COUNT.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.HOST_UP_COUNT.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.CPU_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MEM_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.DISK_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MIN_CPU_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MAX_CPU_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MIN_MEM_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MAX_MEM_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MIN_DISK_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MAX_DISK_USAGE.value)

        # no permission
        self.service.users.remove(self.user)
        response = self.query_response(service_id=service_id, query_tag=ServerQueryChoices.CPU_USAGE.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.HOST_COUNT.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.HOST_UP_COUNT.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.CPU_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MEM_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.DISK_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MIN_CPU_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MAX_CPU_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MIN_MEM_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MAX_MEM_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MIN_DISK_USAGE.value)
        self.query_ok_test(service_id=service_id, query_tag=ServerQueryChoices.MAX_DISK_USAGE.value)


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
