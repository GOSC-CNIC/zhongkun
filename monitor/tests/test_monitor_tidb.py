from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_user, get_or_create_service, MyAPITestCase, get_or_create_org_data_center
from monitor.models import (
    MonitorJobTiDB, MonitorProvider
)
from monitor.managers import TiDBQueryChoices
from .tests import get_or_create_monitor_job_tidb


class MonitorUnitTiDBTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')

    def test_list_unit(self):
        odc = get_or_create_org_data_center()
        unit_tidb1 = MonitorJobTiDB(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            org_data_center=odc
        )
        unit_tidb1.save(force_insert=True)

        unit_tidb2 = MonitorJobTiDB(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
            org_data_center=odc
        )
        unit_tidb2.save(force_insert=True)

        unit_tidb3 = MonitorJobTiDB(
            name='name3', name_en='name_en3', job_tag='job_tag3', sort_weight=3,
        )
        unit_tidb3.save(force_insert=True)

        unit_tidb4 = MonitorJobTiDB(
            name='name4', name_en='name_en4', job_tag='job_tag4',  sort_weight=8,
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
        self.assertKeysIn(['id', "name", "name_en", "job_tag", 'creation', 'remark', 'version',
                           'sort_weight', 'grafana_url', 'dashboard_url', 'org_data_center'
                           ], response.data['results'][0])
        self.assertEqual(unit_tidb4.id, response.data['results'][0]['id'])
        self.assertIsNone(response.data['results'][0]['org_data_center'])

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
        self.assertKeysIn([
            'id', "name", "name_en", 'sort_weight', 'organization'], response.data['results'][0]['org_data_center'])
        self.assertKeysIn([
            'id', "name", "name_en", 'sort_weight'], response.data['results'][0]['org_data_center']['organization'])

        # ---- test org data center admin ----
        unit_tidb1.users.remove(self.user)
        unit_tidb4.users.remove(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # unit_tidb1, unit_tidb2
        unit_tidb2.org_data_center.users.add(self.user)     # 关联的数据中心管理员权限
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_tidb1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_tidb2.id, response.data['results'][1]['id'])

        # unit_tidb1, unit_tidb4, unit_tidb2
        unit_tidb4.users.add(self.user)
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
        query = parse.urlencode(query={'organization_id': odc.organization_id})
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
        query = parse.urlencode(query={'organization_id': odc.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_tidb1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_tidb2.id, response.data['results'][1]['id'])

    def query_response(self, monitor_unit_id: str = None, query_tag: str = None):
        querys = {}
        if monitor_unit_id:
            querys['monitor_unit_id'] = monitor_unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('api:monitor-tidb-query-list')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, monitor_unit_id: str, query_tag: str):
        response = self.query_response(monitor_unit_id=monitor_unit_id, query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        if response.data:
            data_item = response.data[0]
            self.assertKeysIn(["metric", "value", "monitor"], data_item)
            if data_item["value"] is not None:
                self.assertIsInstance(data_item["value"], list)
                self.assertEqual(len(data_item["value"]), 2)
            self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], data_item["monitor"])

        return response

    def test_query(self):
        monitor_job_tidb = get_or_create_monitor_job_tidb()

        # 未认证
        response = self.query_response(
            monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.QPS.value)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)

        response = self.query_response(
            monitor_unit_id=monitor_job_tidb.id, query_tag='test')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.query_response(
            monitor_unit_id='notfound', query_tag=TiDBQueryChoices.QPS.value)
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        # no permission
        response = self.query_response(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.QPS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 服务单元管理员权限测试
        monitor_job_tidb.org_data_center.users.add(self.user)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.QPS.value)
        # 移除服务单元管理员权限
        monitor_job_tidb.org_data_center.users.remove(self.user)

        # no permission
        response = self.query_response(
            monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.QPS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        monitor_job_tidb.users.add(self.user)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.SERVER_DISK_USAGE.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.SERVER_MEM_USAGE.value)
        self.query_ok_test(
            monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.SERVER_CPU_USAGE.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.CURRENT_STORAGE_SIZE.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.STORAGE_CAPACITY.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.REGION_HEALTH.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.REGION_COUNT.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.QPS.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.CONNECTIONS_COUNT.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.TIKV_NODES.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.TIDB_NODES.value)
        self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.PD_NODES.value)

        # no permission
        monitor_job_tidb.users.remove(self.user)
        response = self.query_response(
            monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.QPS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.SERVER_DISK_USAGE.value)
        self.assertTrue(len(r.data) > 1)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.SERVER_MEM_USAGE.value)
        self.assertTrue(len(r.data) > 1)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.QPS.value)
        self.assertTrue(len(r.data) > 6)
        r = self.query_ok_test(
            monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.SERVER_CPU_USAGE.value)
        self.assertTrue(len(r.data) > 1)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.CONNECTIONS_COUNT.value)
        self.assertTrue(len(r.data) > 1)
        r = self.query_ok_test(
            monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.CURRENT_STORAGE_SIZE.value)
        self.assertTrue(len(r.data) == 1)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.STORAGE_CAPACITY.value)
        self.assertTrue(len(r.data) == 1)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.REGION_HEALTH.value)
        self.assertTrue(len(r.data) >= 6)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.REGION_COUNT.value)
        self.assertTrue(len(r.data) == 1)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.TIKV_NODES.value)
        self.assertTrue(len(r.data) == 0 or len(r.data) >= 3)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.TIDB_NODES.value)
        self.assertTrue(len(r.data) == 0 or len(r.data) >= 3)
        r = self.query_ok_test(monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.PD_NODES.value)
        self.assertTrue(len(r.data) == 0 or len(r.data) >= 3)

        # all together
        response = self.query_response(
            monitor_unit_id=monitor_job_tidb.id, query_tag=TiDBQueryChoices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = TiDBQueryChoices.values
        tags.remove(TiDBQueryChoices.ALL_TOGETHER.value)
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
