import time
from urllib import parse

from django.urls import reverse

from apps.app_monitor.models import MonitorJobCeph
from apps.app_monitor.managers import CephQueryChoices, CephQueryV2Choices
from utils.test import (
    get_or_create_user, MyAPITestCase, get_or_create_org_data_center
)

from .tests import get_or_create_monitor_job_ceph


class MonitorCephTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')

    def query_response(self, monitor_unit_id: str = None, query_tag: str = None):
        querys = {}
        if monitor_unit_id:
            querys['monitor_unit_id'] = monitor_unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('monitor-api:ceph-query-list')
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

        self.client.force_login(user=self.user)
        # no permission
        response = self.query_response(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 数据中心管理员权限测试
        monitor_job_ceph.org_data_center.add_admin_user(user=self.user)
        self.query_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value)
        # 移除数据中心管理员权限
        monitor_job_ceph.org_data_center.remove_admin_user(user=self.user)

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

        url = reverse('monitor-api:ceph-query-range')
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
        self.client.force_login(user=self.user)
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

        # 数据中心管理员
        monitor_job_ceph.org_data_center.add_admin_user(user=self.user)
        self.query_range_ok_test(monitor_unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS.value,
                                 start=start, end=end, step=step)

        # no permission
        monitor_job_ceph.org_data_center.remove_admin_user(user=self.user)
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

    def test_list_unit(self):
        odc = get_or_create_org_data_center()
        unit_ceph1 = MonitorJobCeph(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            org_data_center=odc
        )
        unit_ceph1.save(force_insert=True)

        unit_ceph2 = MonitorJobCeph(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
            org_data_center=odc
        )
        unit_ceph2.save(force_insert=True)

        unit_ceph3 = MonitorJobCeph(
            name='name3', name_en='name_en3', job_tag='job_tag3', sort_weight=3,
            org_data_center=None
        )
        unit_ceph3.save(force_insert=True)

        unit_ceph4 = MonitorJobCeph(
            name='name4', name_en='name_en4', job_tag='job_tag4',  sort_weight=8,
            org_data_center=None
        )
        unit_ceph4.save(force_insert=True)

        # 未认证
        url = reverse('monitor-api:unit-ceph-list')
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
                           'sort_weight', 'grafana_url', 'dashboard_url', 'org_data_center'
                           ], response.data['results'][0])
        self.assertEqual(unit_ceph4.id, response.data['results'][0]['id'])
        self.assertIsNone(response.data['results'][0]['org_data_center'])

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
        self.assertKeysIn([
            'id', "name", "name_en", 'sort_weight', 'organization'], response.data['results'][0]['org_data_center'])
        self.assertKeysIn([
            'id', "name", "name_en", 'sort_weight'], response.data['results'][0]['org_data_center']['organization'])

        # unit_ceph1, unit_ceph4, unit_ceph2
        unit_ceph2.org_data_center.add_admin_user(user=self.user)     # 关联的机构数据中心管理员
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
        query = parse.urlencode(query={'organization_id': odc.organization_id})
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
        query = parse.urlencode(query={'organization_id': odc.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_ceph1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_ceph2.id, response.data['results'][1]['id'])

    def query_v2_response(self, unit_id: str = None, query_tag: str = None):
        querys = {}
        if unit_id:
            querys['monitor_unit_id'] = unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('monitor-api:ceph-query-query-v2')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_v2_ok_test(self, unit_id: str, query_tag: str):
        response = self.query_v2_response(unit_id=unit_id, query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)
        self.assertKeysIn([query_tag, "monitor"], response.data)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], response.data["monitor"])
        tag_data = response.data[query_tag]
        if tag_data:
            data_item = tag_data[0]
            self.assertKeysIn(["metric", "value"], data_item)
            if data_item["value"] is not None:
                self.assertIsInstance(data_item["value"], list)
                self.assertEqual(len(data_item["value"]), 2)

        return response

    def test_query_v2(self):
        ceph_unit = get_or_create_monitor_job_ceph()
        ceph_unit_id = ceph_unit.id

        self.client.force_login(user=self.user)
        # no permission
        response = self.query_v2_response(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.HEALTH_STATUS_DETAIL.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 数据中心管理员权限测试
        ceph_unit.org_data_center.add_admin_user(user=self.user)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.HEALTH_STATUS_DETAIL.value)
        # 移除数据中心管理员权限
        ceph_unit.org_data_center.remove_admin_user(user=self.user)

        # no permission
        response = self.query_v2_response(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.HEALTH_STATUS_DETAIL.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        ceph_unit.users.add(self.user)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.HEALTH_STATUS_DETAIL.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.HEALTH_STATUS_DETAIL.value]) >= 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.CLUSTER_SIZE.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.CLUSTER_SIZE.value]) == 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.CLUSTER_USED_SIZE.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.CLUSTER_USED_SIZE.value]) == 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OSD_IN_COUNT.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.OSD_IN_COUNT.value]) == 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OSD_OUT.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.OSD_OUT.value]) >= 0)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OSD_UP_COUNT.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.OSD_UP_COUNT.value]) >= 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OSD_DOWN.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.OSD_DOWN.value]) >= 0)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.MON_STATUS.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.MON_STATUS.value]) >= 3)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.MGR_STATUS.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.MGR_STATUS.value]) >= 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.POOL_META.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.POOL_META.value]) >= 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.PG_ACTIVE.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.PG_ACTIVE.value]) >= 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.PG_UNACTIVE.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.PG_UNACTIVE.value]) >= 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.PG_DEGRADED.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.PG_DEGRADED.value]) >= 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OBJ_DEGRADED.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.OBJ_DEGRADED.value]) == 1)
        r = self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OBJ_MISPLACED.value)
        self.assertTrue(len(r.data[CephQueryV2Choices.OBJ_MISPLACED.value]) == 1)

        # no permission
        ceph_unit.users.remove(self.user)
        response = self.query_v2_response(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.HEALTH_STATUS_DETAIL.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.HEALTH_STATUS_DETAIL.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.CLUSTER_SIZE.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OSD_IN_COUNT.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OSD_UP_COUNT.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.MON_STATUS.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.MGR_STATUS.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.POOL_META.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.PG_DEGRADED.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OBJ_DEGRADED.value)
        self.query_v2_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.OBJ_MISPLACED.value)

        # all together
        response = self.query_v2_response(unit_id=ceph_unit_id, query_tag=CephQueryV2Choices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = CephQueryV2Choices.values
        tags.remove(CephQueryV2Choices.ALL_TOGETHER.value)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], response.data["monitor"])
        for tag in tags:
            self.assertIn(tag, response.data)
            tag_data = response.data[tag]
            self.assertIsInstance(tag_data, list)
            if tag_data:
                data_item = tag_data[0]
                self.assertKeysIn(["metric", "value"], data_item)
                if data_item["value"] is not None:
                    self.assertIsInstance(data_item["value"], list)
                    self.assertEqual(len(data_item["value"]), 2)
