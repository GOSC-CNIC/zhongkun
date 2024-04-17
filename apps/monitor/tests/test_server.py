from urllib import parse

from django.urls import reverse

from apps.monitor.models import MonitorJobServer
from apps.monitor.managers import ServerQueryChoices, ServerQueryV2Choices
from utils.test import get_or_create_user, MyAPITestCase, get_or_create_org_data_center
from .tests import get_or_create_monitor_job_server


class MonitorServerTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')

    def test_list_server_unit(self):
        odc = get_or_create_org_data_center()

        unit_server1 = MonitorJobServer(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10,
            org_data_center=odc
        )
        unit_server1.save(force_insert=True)

        unit_server2 = MonitorJobServer(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=6,
        )
        unit_server2.save(force_insert=True)

        unit_server3 = MonitorJobServer(
            name='name3', name_en='name_en3', job_tag='job_tag3', sort_weight=3,
            org_data_center=odc
        )
        unit_server3.save(force_insert=True)

        unit_server4 = MonitorJobServer(
            name='name4', name_en='name_en4', job_tag='job_tag4',  sort_weight=8,
        )
        unit_server4.save(force_insert=True)

        # 未认证
        url = reverse('monitor-api:unit-server-list')
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
                           'sort_weight', 'grafana_url', 'dashboard_url', 'org_data_center'
                           ], response.data['results'][0])
        self.assertEqual(unit_server4.id, response.data['results'][0]['id'])
        self.assertIsNone(response.data['results'][0]['org_data_center'])

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
        self.assertKeysIn([
            'id', "name", "name_en", 'sort_weight', 'organization'], response.data['results'][0]['org_data_center'])
        self.assertKeysIn([
            'id', "name", "name_en", 'sort_weight'], response.data['results'][0]['org_data_center']['organization'])

        # no
        unit_server1.users.remove(self.user)
        unit_server4.users.remove(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # unit_server1, unit_server3
        odc.users.add(self.user)  # 关联的机构数据中心管理员权限
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_server3.id, response.data['results'][1]['id'])

        # unit_server1, unit_server4, unit_server3
        unit_server4.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_server4.id, response.data['results'][1]['id'])
        self.assertEqual(unit_server3.id, response.data['results'][2]['id'])

        # query "organization_id"
        query = parse.urlencode(query={'organization_id': odc.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_server3.id, response.data['results'][1]['id'])

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
        query = parse.urlencode(query={'organization_id': odc.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(unit_server1.id, response.data['results'][0]['id'])
        self.assertEqual(unit_server3.id, response.data['results'][1]['id'])

    def query_response(self, monitor_unit_id: str = None, query_tag: str = None):
        querys = {}
        if monitor_unit_id:
            querys['monitor_unit_id'] = monitor_unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('monitor-api:server-query-list')
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
        self.client.force_login(user=self.user)
        monitor_server_unit = get_or_create_monitor_job_server()
        server_unit_id = monitor_server_unit.id

        # no permission
        response = self.query_response(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 服务单元管理员权限测试
        monitor_server_unit.org_data_center.users.add(self.user)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)
        # 移除服务单元管理员权限
        monitor_server_unit.org_data_center.users.remove(self.user)

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

        # data center admin
        monitor_server_unit.org_data_center.users.add(self.user)
        self.query_ok_test(monitor_unit_id=server_unit_id, query_tag=ServerQueryChoices.HEALTH_STATUS.value)

        # no permission
        monitor_server_unit.org_data_center.users.remove(self.user)
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

    def query_v2_response(self, unit_id: str = None, query_tag: str = None):
        querys = {}
        if unit_id:
            querys['monitor_unit_id'] = unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('monitor-api:server-query-query-v2')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_v2_ok_test(self, unit_id: str, query_tag: str):
        response = self.query_v2_response(unit_id=unit_id, query_tag=query_tag)
        if response.status_code != 200:
            print(response.data)
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
        self.client.force_login(user=self.user)
        server_unit = get_or_create_monitor_job_server()
        server_unit_id = server_unit.id

        # no permission
        response = self.query_v2_response(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_UP.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 服务单元管理员权限测试
        server_unit.org_data_center.users.add(self.user)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_UP.value)
        # 移除服务单元管理员权限
        server_unit.org_data_center.users.remove(self.user)

        # no permission
        response = self.query_v2_response(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_CPU_USAGE.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # admin permission
        server_unit.users.add(self.user)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_UP.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_DOWN.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_BOOT_TIME.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_CPU_COUNT.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_CPU_USAGE.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_MEM_SIZE.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_MEM_AVAIL.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_ROOT_DIR_SIZE.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_ROOT_DIR_AVAIL_SIZE.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_NET_RATE_IN.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_NET_RATE_OUT.value)

        # no permission
        server_unit.users.remove(self.user)
        response = self.query_v2_response(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_NET_RATE_IN.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # data center admin
        server_unit.org_data_center.users.add(self.user)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_NET_RATE_OUT.value)

        # no permission
        server_unit.org_data_center.users.remove(self.user)
        response = self.query_v2_response(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_CPU_USAGE.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        self.user.set_federal_admin()
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_UP.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_DOWN.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_BOOT_TIME.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_CPU_COUNT.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_CPU_USAGE.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_MEM_SIZE.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_MEM_AVAIL.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_ROOT_DIR_SIZE.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_ROOT_DIR_AVAIL_SIZE.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_NET_RATE_IN.value)
        self.query_v2_ok_test(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.HOST_NET_RATE_OUT.value)

        # all together
        response = self.query_v2_response(unit_id=server_unit_id, query_tag=ServerQueryV2Choices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = ServerQueryV2Choices.values
        tags.remove(ServerQueryV2Choices.ALL_TOGETHER.value)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "creation"], response.data["monitor"])
        for tag in tags:
            self.assertIn(tag, response.data)
            tag_data = response.data[tag]
            self.assertIsInstance(tag_data, list)
            if tag_data:
                data_item = tag_data[0]
                self.assertKeysIn(["value", "metric"], data_item)
                if data_item["value"] is not None:
                    self.assertIsInstance(data_item["value"], list)
                    self.assertEqual(len(data_item["value"]), 2)
