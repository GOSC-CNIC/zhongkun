from urllib import parse

from django.urls import reverse

from apps.app_screenvis.managers import CephQueryChoices, HostQueryChoices, TiDBQueryChoices
from . import MyAPITestCase, get_or_create_metric_ceph, get_or_create_metric_host, get_or_create_metric_tidb


class MetricCephTests(MyAPITestCase):
    def setUp(self):
        pass

    def query_response(self, unit_id, query_tag: str):
        querys = {}
        if unit_id:
            querys['unit_id'] = unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('screenvis-api:ceph-query')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, unit_id: int, query_tag: str):
        response = self.query_response(unit_id=unit_id, query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)
        self.assertKeysIn([query_tag, "monitor"], response.data)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "unit_type", 'creation_time'], response.data["monitor"])
        tag_data = response.data[query_tag]
        if tag_data:
            data_item = tag_data[0]
            self.assertKeysIn(["metric", "value"], data_item)
            if data_item["value"] is not None:
                self.assertIsInstance(data_item["value"], list)
                self.assertEqual(len(data_item["value"]), 2)

        return response

    def test_query(self):
        ceph_unit = get_or_create_metric_ceph()
        ceph_unit_id = ceph_unit.id

        response = self.query_response(unit_id=666, query_tag=CephQueryChoices.MGR_STATUS.value)
        self.assertEqual(response.status_code, 404)
        response = self.query_response(unit_id='666', query_tag=CephQueryChoices.MGR_STATUS.value)
        self.assertEqual(response.status_code, 404)
        response = self.query_response(unit_id='xxx', query_tag=CephQueryChoices.MGR_STATUS.value)
        self.assertEqual(response.status_code, 400)
        response = self.query_response(unit_id=ceph_unit_id, query_tag='xxx')
        self.assertEqual(response.status_code, 400)

        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.HEALTH_STATUS_DETAIL.value)
        self.assertTrue(len(r.data[CephQueryChoices.HEALTH_STATUS_DETAIL.value]) >= 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_SIZE.value)
        self.assertTrue(len(r.data[CephQueryChoices.CLUSTER_SIZE.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.CLUSTER_USED_SIZE.value)
        self.assertTrue(len(r.data[CephQueryChoices.CLUSTER_USED_SIZE.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_IN_COUNT.value)
        self.assertTrue(len(r.data[CephQueryChoices.OSD_IN_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_OUT_COUNT.value)
        self.assertTrue(len(r.data[CephQueryChoices.OSD_OUT_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_UP_COUNT.value)
        self.assertTrue(len(r.data[CephQueryChoices.OSD_UP_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.OSD_DOWN_COUNT.value)
        self.assertTrue(len(r.data[CephQueryChoices.OSD_DOWN_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.MON_STATUS.value)
        self.assertTrue(len(r.data[CephQueryChoices.MON_STATUS.value]) >= 3)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.MGR_STATUS.value)
        self.assertTrue(len(r.data[CephQueryChoices.MGR_STATUS.value]) >= 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.POOL_COUNT.value)
        self.assertTrue(len(r.data[CephQueryChoices.POOL_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.PG_ACTIVE_COUNT.value)
        self.assertTrue(len(r.data[CephQueryChoices.PG_ACTIVE_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.PG_UNACTIVE_COUNT.value)
        self.assertTrue(len(r.data[CephQueryChoices.PG_UNACTIVE_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.PG_DEGRADED_COUNT.value)
        self.assertTrue(len(r.data[CephQueryChoices.PG_DEGRADED_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.OBJ_DEGRADED.value)
        self.assertTrue(len(r.data[CephQueryChoices.OBJ_DEGRADED.value]) == 1)
        r = self.query_ok_test(unit_id=ceph_unit_id, query_tag=CephQueryChoices.OBJ_MISPLACED.value)
        self.assertTrue(len(r.data[CephQueryChoices.OBJ_MISPLACED.value]) == 1)

        # all together
        response = self.query_response(unit_id=ceph_unit_id, query_tag=CephQueryChoices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = CephQueryChoices.values
        tags.remove(CephQueryChoices.ALL_TOGETHER.value)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "unit_type", 'creation_time'], response.data["monitor"])
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


class MetricHostTests(MyAPITestCase):
    def setUp(self):
        pass

    def query_response(self, unit_id, query_tag: str):
        querys = {}
        if unit_id:
            querys['unit_id'] = unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('screenvis-api:host-query')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, unit_id: int, query_tag: str):
        response = self.query_response(unit_id=unit_id, query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)
        self.assertKeysIn([query_tag, "monitor"], response.data)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "unit_type", 'creation_time'], response.data["monitor"])
        tag_data = response.data[query_tag]
        if tag_data:
            data_item = tag_data[0]
            self.assertKeysIn(["metric", "value"], data_item)
            if data_item["value"] is not None:
                self.assertIsInstance(data_item["value"], list)
                self.assertEqual(len(data_item["value"]), 2)

        return response

    def test_query(self):
        host_unit = get_or_create_metric_host()
        host_unit_id = host_unit.id

        response = self.query_response(unit_id=666, query_tag=HostQueryChoices.HOST_UP_COUNT.value)
        self.assertEqual(response.status_code, 404)
        response = self.query_response(unit_id='666', query_tag=HostQueryChoices.HOST_UP_COUNT.value)
        self.assertEqual(response.status_code, 404)
        response = self.query_response(unit_id='xxx', query_tag=HostQueryChoices.HOST_UP_COUNT.value)
        self.assertEqual(response.status_code, 400)
        response = self.query_response(unit_id=host_unit_id, query_tag='xxx')
        self.assertEqual(response.status_code, 400)

        r = self.query_ok_test(unit_id=host_unit_id, query_tag=HostQueryChoices.HOST_UP_COUNT.value)
        self.assertTrue(len(r.data[HostQueryChoices.HOST_UP_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=host_unit_id, query_tag=HostQueryChoices.HOST_DOWN.value)
        self.assertTrue(len(r.data[HostQueryChoices.HOST_DOWN.value]) >= 0)

        # all together
        response = self.query_response(unit_id=host_unit_id, query_tag=HostQueryChoices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = HostQueryChoices.values
        tags.remove(HostQueryChoices.ALL_TOGETHER.value)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "unit_type", 'creation_time'], response.data["monitor"])
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


class MetricTiDBTests(MyAPITestCase):
    def setUp(self):
        pass

    def query_response(self, unit_id, query_tag: str):
        querys = {}
        if unit_id:
            querys['unit_id'] = unit_id

        if query_tag:
            querys['query'] = query_tag

        url = reverse('screenvis-api:tidb-query')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, unit_id: int, query_tag: str):
        response = self.query_response(unit_id=unit_id, query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)
        self.assertKeysIn([query_tag, "monitor"], response.data)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "unit_type", 'creation_time'], response.data["monitor"])
        tag_data = response.data[query_tag]
        if tag_data:
            data_item = tag_data[0]
            self.assertKeysIn(["metric", "value"], data_item)
            if data_item["value"] is not None:
                self.assertIsInstance(data_item["value"], list)
                self.assertEqual(len(data_item["value"]), 2)

        return response

    def test_query(self):
        tidb_unit = get_or_create_metric_tidb()
        tidb_unit_id = tidb_unit.id

        response = self.query_response(unit_id=666, query_tag=TiDBQueryChoices.CONNECTIONS_COUNT.value)
        self.assertEqual(response.status_code, 404)
        response = self.query_response(unit_id='666', query_tag=TiDBQueryChoices.CONNECTIONS_COUNT.value)
        self.assertEqual(response.status_code, 404)
        response = self.query_response(unit_id='xxx', query_tag=TiDBQueryChoices.CONNECTIONS_COUNT.value)
        self.assertEqual(response.status_code, 400)
        response = self.query_response(unit_id=tidb_unit_id, query_tag='xxx')
        self.assertEqual(response.status_code, 400)

        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.TIDB_NODES.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.TIDB_NODES.value]) >= 3)
        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.TIKV_NODES.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.TIKV_NODES.value]) >= 3)
        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.PD_NODES.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.PD_NODES.value]) >= 3)
        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.CONNECTIONS_COUNT.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.CONNECTIONS_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.QPS_COUNT.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.QPS_COUNT.value]) == 1)
        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.STORAGE.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.STORAGE.value]) == 2)
        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.SERVER_CPU_USAGE.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.SERVER_CPU_USAGE.value]) == 1)
        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.SERVER_MEM_SIZE.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.SERVER_MEM_SIZE.value]) == 1)
        r = self.query_ok_test(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.SERVER_MEM_AVAIL.value)
        self.assertTrue(len(r.data[TiDBQueryChoices.SERVER_MEM_AVAIL.value]) == 1)

        # all together
        response = self.query_response(unit_id=tidb_unit_id, query_tag=TiDBQueryChoices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = TiDBQueryChoices.values
        tags.remove(TiDBQueryChoices.ALL_TOGETHER.value)
        self.assertKeysIn(["name", "name_en", "job_tag", "id", "unit_type", 'creation_time'], response.data["monitor"])
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
