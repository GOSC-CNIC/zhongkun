from decimal import Decimal
from urllib import parse
from order.managers.order import OrderManager
from scan.models import VtScanService, VtTask
from django.urls import reverse
from django.conf import settings
from bill.models import PayApp, PayAppService
from utils.test import (
    get_or_create_user,
    get_or_create_organization,
    MyAPITestCase,
)
from order.models import Price


class ScanTaskTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password="password")
        self.user2 = get_or_create_user(username="tom@cnic.cn", password="password")

    def test_task_list(self):
        # NotAuthenticated
        base_url = reverse("scan-api:task-list")
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=401, code="NotAuthenticated", response=r)

        # BadType
        self.client.force_login(self.user)
        query = parse.urlencode(query={"type": "xx"})
        r = self.client.get(path=f"{base_url}?{query}")
        self.assertEqual(r.status_code, 400)

        # ok, no data
        self.client.force_login(self.user)
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(
            keys=["count", "page_num", "page_size", "results"], container=r.data
        )
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(r.data["page_num"], 1)
        self.assertIsInstance(r.data["results"], list)
        self.assertEqual(len(r.data["results"]), 0)

        # add data
        user_scan_task1 = VtTask(
            name="user_task1",
            target="http://test.com/",
            type="web",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid1",
        )
        user_scan_task1.save(force_insert=True)

        user_scan_task2 = VtTask(
            name="user_task2",
            target="http://test2.com/",
            type="web",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid2",
        )
        user_scan_task2.save(force_insert=True)

        user_scan_task3 = VtTask(
            name="user_task3",
            target="http://test3.com/",
            type="web",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid3",
        )
        user_scan_task3.save(force_insert=True)

        user2_scan_task1 = VtTask(
            name="user_task6",
            target="3.3.3.3",
            type="host",
            user=self.user2,
            remark="user task test",
            payment_history_id="testpaymenthistoryid1",
        )
        user2_scan_task1.save(force_insert=True)

        user2_scan_task2 = VtTask(
            name="user_task6",
            target="http://test1.com/",
            type="web",
            user=self.user2,
            remark="user task test",
            payment_history_id="testpaymenthistoryid2",
        )
        user2_scan_task2.save(force_insert=True)

        user_scan_task4 = VtTask(
            name="user_task4",
            target="1.1.1.1",
            type="host",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid4",
        )
        user_scan_task4.save(force_insert=True)

        user_scan_task5 = VtTask(
            name="user_task5",
            target="2.2.2.2",
            type="host",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid5",
        )
        user_scan_task5.save(force_insert=True)

        user_scan_task6 = VtTask(
            name="user_task6",
            target="3.3.3.3",
            type="host",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid6",
        )
        user_scan_task6.save(force_insert=True)

        # ok, list web
        query = parse.urlencode(query={"type": "web"})
        r = self.client.get(path=f"{base_url}?{query}")
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(
            keys=["count", "page_num", "page_size", "results"], container=r.data
        )
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(r.data["page_num"], 1)
        self.assertEqual(len(r.data["results"]), 3)
        self.assertKeysIn(
            keys=[
                "id",
                "name",
                "target",
                "type",
                "task_status",
                "user",
                "create_time",
                "remark",
                "update_time",
            ],
            container=r.data["results"][0],
        )
        self.assert_is_subdict_of(
            sub={
                "name": user_scan_task3.name,
                "target": user_scan_task3.target,
                "remark": user_scan_task3.remark,
                "task_status": user_scan_task3.task_status,
                "type": user_scan_task3.type,
            },
            d=r.data["results"][0],
        )
        self.assertEqual(r.data["results"][0]["user"]["id"], self.user.id)
        self.assertEqual(r.data["results"][0]["user"]["username"], self.user.username)

        # ok, list host
        query = parse.urlencode(query={"type": "host"})
        r = self.client.get(path=f"{base_url}?{query}")
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(
            keys=["count", "page_num", "page_size", "results"], container=r.data
        )
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(r.data["page_num"], 1)
        self.assertEqual(len(r.data["results"]), 3)
        self.assertKeysIn(
            keys=[
                "id",
                "name",
                "target",
                "type",
                "task_status",
                "user",
                "create_time",
                "remark",
                "update_time",
            ],
            container=r.data["results"][0],
        )
        self.assert_is_subdict_of(
            sub={
                "name": user_scan_task6.name,
                "target": user_scan_task6.target,
                "remark": user_scan_task6.remark,
                "task_status": user_scan_task6.task_status,
                "type": user_scan_task6.type,
            },
            d=r.data["results"][0],
        )
        self.assertEqual(r.data["results"][0]["user"]["id"], self.user.id)
        self.assertEqual(r.data["results"][0]["user"]["username"], self.user.username)

        # ok, list all
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(
            keys=["count", "page_num", "page_size", "results"], container=r.data
        )
        self.assertEqual(r.data["count"], 6)
        self.assertEqual(r.data["page_num"], 1)
        self.assertEqual(len(r.data["results"]), 6)
        self.assertKeysIn(
            keys=[
                "id",
                "name",
                "target",
                "type",
                "task_status",
                "user",
                "create_time",
                "remark",
                "update_time",
            ],
            container=r.data["results"][0],
        )
        self.assert_is_subdict_of(
            sub={
                "name": user_scan_task6.name,
                "target": user_scan_task6.target,
                "remark": user_scan_task6.remark,
                "task_status": user_scan_task6.task_status,
                "type": user_scan_task6.type,
            },
            d=r.data["results"][0],
        )
        self.assert_is_subdict_of(
            sub={
                "name": user_scan_task3.name,
                "target": user_scan_task3.target,
                "remark": user_scan_task3.remark,
                "task_status": user_scan_task3.task_status,
                "type": user_scan_task3.type,
            },
            d=r.data["results"][3],
        )
        self.assertEqual(r.data["results"][0]["user"]["id"], self.user.id)
        self.assertEqual(r.data["results"][0]["user"]["username"], self.user.username)

        # ok, list, page_size
        query = parse.urlencode(query={"page_size": 2})
        r = self.client.get(path=f"{base_url}?{query}")
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(
            keys=["count", "page_num", "page_size", "results"], container=r.data
        )
        self.assertEqual(r.data["count"], 6)
        self.assertEqual(r.data["page_num"], 1)
        self.assertEqual(r.data["page_size"], 2)
        self.assertEqual(len(r.data["results"]), 2)
        self.assertEqual(r.data["results"][0]["id"], user_scan_task6.id)
        self.assertEqual(r.data["results"][1]["id"], user_scan_task5.id)

        # ok, list, page, page_size
        query = parse.urlencode(query={"page": 2, "page_size": 2})
        r = self.client.get(path=f"{base_url}?{query}")
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(
            keys=["count", "page_num", "page_size", "results"], container=r.data
        )
        self.assertEqual(r.data["count"], 6)
        self.assertEqual(r.data["page_num"], 2)
        self.assertEqual(r.data["page_size"], 2)
        self.assertEqual(len(r.data["results"]), 2)
        self.assertEqual(r.data["results"][0]["id"], user_scan_task4.id)
        self.assertEqual(r.data["results"][1]["id"], user_scan_task3.id)

    def test_create_task(self):
        # 价格
        price = Price(
            vm_ram=Decimal('0.012'),
            vm_cpu=Decimal('0.066'),
            vm_disk=Decimal('0.122'),
            vm_pub_ip=Decimal('0.66'),
            vm_upstream=Decimal('0.33'),
            vm_downstream=Decimal('1.44'),
            vm_disk_snap=Decimal('0.65'),
            disk_size=Decimal('1.02'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            scan_web=Decimal('10'),
            scan_host=Decimal('20'),
            prepaid_discount=66
        )
        price.save()
        # 扫描任务订单创建
        app = PayApp(name="app", id=settings.PAYMENT_BALANCE["app_id"])
        app.save()
        app = app
        po = get_or_create_organization(name="机构")
        po.save()
        app_service1 = PayAppService(
            name="scan",
            app=app,
            orgnazition=po,
            app_id=settings.PAYMENT_BALANCE["app_id"],
        )
        app_service1.save()

        scanservice = VtScanService(
            name="安全扫描服务配置信息",
            name_en="scan",
            status=VtScanService.Status.ENABLE,
            remark="scan test",
        )
        scanservice.save()

        # NotAuthenticated
        url = reverse("scan-api:task-list")
        r = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "scheme": "https://",
                "hostname": "test.c",
                "uri": "/",
                "remark": "test",
            },
            content_type="application/json",
        )
        self.assertErrorResponse(status_code=401, code="NotAuthenticated", response=r)

        # InvalidUrl
        self.client.force_login(self.user)
        r = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "scheme": "https://",
                "hostname": "test.c",
                "uri": "/",
                "remark": "test",
            },
        )
        self.assertErrorResponse(status_code=400, code="InvalidUrl", response=r)

        # InvalidScanType
        self.client.force_login(self.user)
        r = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "remark": "test",
            },
        )
        self.assertErrorResponse(status_code=400, code="InvalidScanType", response=r)

        # InvalidIp
        self.client.force_login(self.user)
        r = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "0.0",
            },
        )
        self.assertErrorResponse(status_code=400, code="InvalidIp", response=r)

        # ServiceNoPayAppServiceId
        response = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "1.1.1.1",
            },
        )
        self.assertErrorResponse(
            status_code=409, code="ServiceNoPayAppServiceId", response=response
        )
        scan_ins = VtScanService.get_instance()
        scan_ins.pay_app_service_id = app_service1.id
        scan_ins.save(update_fields=["pay_app_service_id"])

        # ok host scan
        omsg = OrderManager()
        self.client.force_login(self.user)
        response = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "1.1.1.1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            keys=["order_id"],
            container=response.data,
        )
        order = omsg.get_order(response.data["order_id"])
        self.assertEqual(order.order_type, "new")
        self.assertEqual(order.status, "unpaid")
        self.assertEqual(order.resource_type, "scan")
        self.assertEqual(order.user_id, self.user.id)
        self.assertEqual(order.app_service_id, app_service1.id)
        scanconfig = order.instance_config
        web_url = scanconfig.get("web_url", "")
        self.assertEqual(web_url, "")
        self.assertEqual(scanconfig["host_addr"], "1.1.1.1")
        self.assertEqual(scanconfig["remark"], "test")

        # ok web scan
        self.client.force_login(self.user)
        response = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "remark": "test",
                "scheme": "https://",
                "hostname": "test2.com",
                "uri": "/",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            keys=["order_id"],
            container=response.data,
        )
        order = omsg.get_order(response.data["order_id"])
        self.assertEqual(order.order_type, "new")
        self.assertEqual(order.status, "unpaid")
        self.assertEqual(order.resource_type, "scan")
        self.assertEqual(order.user_id, self.user.id)
        self.assertEqual(order.app_service_id, app_service1.id)
        scanconfig = order.instance_config
        host_addr = scanconfig.get("host_addr", "")
        self.assertEqual(host_addr, "")
        self.assertEqual(scanconfig["web_url"], "https://test2.com/")

        # ok web and host scan
        self.client.force_login(self.user)
        response = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "remark": "test",
                "scheme": "https://",
                "hostname": "test2.com",
                "uri": "/",
                "ipaddr": "2.2.2.2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            keys=["order_id"],
            container=response.data,
        )
        order = omsg.get_order(response.data["order_id"])
        self.assertEqual(order.order_type, "new")
        self.assertEqual(order.status, "unpaid")
        self.assertEqual(order.resource_type, "scan")
        self.assertEqual(order.user_id, self.user.id)
        self.assertEqual(order.app_service_id, app_service1.id)
        scanconfig = order.instance_config
        self.assertEqual(scanconfig["host_addr"], "2.2.2.2")
        self.assertEqual(scanconfig["web_url"], "https://test2.com/")
