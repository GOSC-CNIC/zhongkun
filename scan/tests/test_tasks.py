from decimal import Decimal
from datetime import timedelta
from urllib import parse

from utils.model import OwnerType
from ..models import VtScanService, VtTask

from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from bill.models import CashCoupon, PayApp, PayAppService, PaymentHistory
from utils.test import (
    get_or_create_user,
    get_or_create_organization,
    MyAPITestCase,
)


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

    def test_create_website_task(self):
        # 余额支付有关配置
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
            host_scan_price=Decimal("50.00"),
            web_scan_price=Decimal("100.00"),
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

        # MissingCouponIDs
        self.client.force_login(self.user)
        r = self.client.post(
            path=url,
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "1.1.1.1",
            },
        )
        self.assertErrorResponse(status_code=400, code="MissingCouponIDs", response=r)

        # 添加资源券
        now_time = timezone.now()
        coupon1_user = CashCoupon(
            face_value=Decimal("30"),
            balance=Decimal("30"),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=app_service1.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id=None,
        )
        coupon1_user.save(force_insert=True)

        # 添加资源券
        now_time = timezone.now()
        coupon2_user = CashCoupon(
            face_value=Decimal("40"),
            balance=Decimal("40"),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=app_service1.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id=None,
        )
        coupon2_user.save(force_insert=True)

        # 添加资源券
        now_time = timezone.now()
        coupon3_user = CashCoupon(
            face_value=Decimal("100"),
            balance=Decimal("100"),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=app_service1.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id=None,
        )
        coupon3_user.save(force_insert=True)

        # 添加资源券
        now_time = timezone.now()
        coupon4_user = CashCoupon(
            face_value=Decimal("200"),
            balance=Decimal("200"),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=app_service1.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id=None,
        )
        coupon4_user.save(force_insert=True)

        # InvalidCouponIDs
        query = parse.urlencode(query={"coupon_ids": ["test", ""]}, doseq=True)
        response = self.client.post(
            f"{url}?{query}",
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "1.1.1.1",
            },
        )
        self.assertErrorResponse(
            status_code=400, code="InvalidCouponIDs", response=response
        )

        #  TooManyCouponIDs
        query = parse.urlencode(
            query={"coupon_ids": ["test", "1", "2", "3", "4", "5"]}, doseq=True
        )
        response = self.client.post(
            f"{url}?{query}",
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "1.1.1.1",
            },
        )
        self.assertErrorResponse(
            status_code=400, code="TooManyCouponIDs", response=response
        )

        # DuplicateCouponIDExist
        query = parse.urlencode(
            query={"coupon_ids": ["1", "1", "2", "4", "5"]}, doseq=True
        )
        response = self.client.post(
            f"{url}?{query}",
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "1.1.1.1",
            },
        )
        self.assertErrorResponse(
            status_code=400, code="DuplicateCouponIDExist", response=response
        )

        # ServiceNoPayAppServiceId
        query = parse.urlencode(query={"coupon_ids": ["1"]}, doseq=True)
        response = self.client.post(
            f"{url}?{query}",
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

        # CouponBalanceNotEnough
        self.client.force_login(self.user)
        query = parse.urlencode(query={"coupon_ids": [coupon1_user.id]}, doseq=True)
        response = self.client.post(
            f"{url}?{query}",
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "1.1.1.1",
            },
        )
        self.assertErrorResponse(
            status_code=409, code="CouponBalanceNotEnough", response=response
        )

        # ok pay host scan(50) coupon1(30-30) coupon2(40-20)
        coupon1_user.refresh_from_db()
        coupon2_user.refresh_from_db()
        self.client.force_login(self.user)
        query = parse.urlencode(
            query={"coupon_ids": [coupon1_user.id, coupon2_user.id]}, doseq=True
        )
        response = self.client.post(
            f"{url}?{query}",
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "1.1.1.1",
            },
        )
        self.assertEqual(response.status_code, 200)
        coupon1_user.refresh_from_db()
        self.assertEqual(coupon1_user.balance, Decimal("0"))
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.balance, Decimal("20"))
        self.assertEqual(len(response.data), 1)
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
            container=response.data[0],
        )
        user_scan_task7 = VtTask.objects.filter(id=response.data[0]["id"]).first()
        self.assert_is_subdict_of(
            sub={
                "name": user_scan_task7.name,
                "target": user_scan_task7.target,
                "remark": user_scan_task7.remark,
                "task_status": user_scan_task7.task_status,
                "type": user_scan_task7.type,
            },
            d=response.data[0],
        )
        self.assertEqual(user_scan_task7.target, "1.1.1.1")
        # 支付记录确认
        pay_history1 = PaymentHistory.objects.filter(
            order_id=user_scan_task7.id
        ).first()
        self.assertEqual(pay_history1.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history1.payable_amounts, Decimal("50"))
        self.assertEqual(pay_history1.amounts, Decimal("0"))
        self.assertEqual(pay_history1.coupon_amount, Decimal("-50"))
        self.assertEqual(pay_history1.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history1.payer_id, self.user.id)
        self.assertEqual(pay_history1.payer_name, self.user.username)
        self.assertEqual(pay_history1.executor, self.user.username)
        self.assertEqual(
            pay_history1.payment_method, PaymentHistory.PaymentMethod.CASH_COUPON.value
        )
        self.assertEqual(pay_history1.payment_account, "")
        self.assertEqual(pay_history1.app_service_id, app_service1.id)
        self.assertEqual(pay_history1.instance_id, "")
        self.assertEqual(pay_history1.app_id, settings.PAYMENT_BALANCE["app_id"])
        self.assertEqual(pay_history1.subject, "安全扫描计费")

        # ok pay web scan(100) coupon2(20-20) coupon3(100-80)
        coupon2_user.refresh_from_db()
        coupon3_user.refresh_from_db()
        self.client.force_login(self.user)
        query = parse.urlencode(
            query={"coupon_ids": [coupon2_user.id, coupon3_user.id]}, doseq=True
        )
        response = self.client.post(
            f"{url}?{query}",
            data={
                "name": "name-test",
                "remark": "test",
                "scheme": "https://",
                "hostname": "test.com",
                "uri": "/",
            },
        )
        self.assertEqual(response.status_code, 200)
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.balance, Decimal("0"))
        coupon3_user.refresh_from_db()
        self.assertEqual(coupon3_user.balance, Decimal("20"))
        self.assertEqual(len(response.data), 1)
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
            container=response.data[0],
        )
        user_scan_task8 = VtTask.objects.filter(id=response.data[0]["id"]).first()
        self.assert_is_subdict_of(
            sub={
                "name": user_scan_task8.name,
                "target": user_scan_task8.target,
                "remark": user_scan_task8.remark,
                "task_status": user_scan_task8.task_status,
                "type": user_scan_task8.type,
            },
            d=response.data[0],
        )
        self.assertEqual(user_scan_task8.target, "https://test.com/")
        # 支付记录确认
        pay_history1 = PaymentHistory.objects.filter(
            order_id=user_scan_task8.id
        ).first()
        self.assertEqual(pay_history1.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history1.payable_amounts, Decimal("100"))
        self.assertEqual(pay_history1.amounts, Decimal("0"))
        self.assertEqual(pay_history1.coupon_amount, Decimal("-100"))
        self.assertEqual(pay_history1.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history1.payer_id, self.user.id)
        self.assertEqual(pay_history1.payer_name, self.user.username)
        self.assertEqual(pay_history1.executor, self.user.username)
        self.assertEqual(
            pay_history1.payment_method, PaymentHistory.PaymentMethod.CASH_COUPON.value
        )
        self.assertEqual(pay_history1.payment_account, "")
        self.assertEqual(pay_history1.app_service_id, app_service1.id)
        self.assertEqual(pay_history1.instance_id, "")
        self.assertEqual(pay_history1.app_id, settings.PAYMENT_BALANCE["app_id"])
        self.assertEqual(pay_history1.subject, "安全扫描计费")

        # ok pay web and host scan(150) coupon4(200-150)
        coupon3_user.refresh_from_db()
        self.client.force_login(self.user)
        query = parse.urlencode(query={"coupon_ids": [coupon4_user.id]}, doseq=True)
        response = self.client.post(
            f"{url}?{query}",
            data={
                "name": "name-test",
                "remark": "test",
                "ipaddr": "2.2.2.2",
                "scheme": "https://",
                "hostname": "test2.com",
                "uri": "/",
            },
        )
        self.assertEqual(response.status_code, 200)
        coupon4_user.refresh_from_db()
        self.assertEqual(coupon4_user.balance, Decimal("50"))
        self.assertEqual(len(response.data), 2)
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
            container=response.data[0],
        )
        user_scan_task9 = VtTask.objects.filter(id=response.data[0]["id"]).first()
        user_scan_task10 = VtTask.objects.filter(id=response.data[1]["id"]).first()
        self.assert_is_subdict_of(
            sub={
                "name": user_scan_task9.name,
                "target": user_scan_task9.target,
                "remark": user_scan_task9.remark,
                "task_status": user_scan_task9.task_status,
                "type": user_scan_task9.type,
            },
            d=response.data[0],
        )
        self.assert_is_subdict_of(
            sub={
                "name": user_scan_task10.name,
                "target": user_scan_task10.target,
                "remark": user_scan_task10.remark,
                "task_status": user_scan_task10.task_status,
                "type": user_scan_task10.type,
            },
            d=response.data[1],
        )
        self.assertEqual(user_scan_task9.target, "https://test2.com/")
        self.assertEqual(user_scan_task10.target, "2.2.2.2")
        # 支付记录确认
        pay_history1 = PaymentHistory.objects.filter(
            id=user_scan_task9.payment_history_id
        ).first()
        self.assertEqual(pay_history1.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history1.payable_amounts, Decimal("150"))
        self.assertEqual(pay_history1.amounts, Decimal("0"))
        self.assertEqual(pay_history1.coupon_amount, Decimal("-150"))
        self.assertEqual(pay_history1.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history1.payer_id, self.user.id)
        self.assertEqual(pay_history1.payer_name, self.user.username)
        self.assertEqual(pay_history1.executor, self.user.username)
        self.assertEqual(
            pay_history1.payment_method, PaymentHistory.PaymentMethod.CASH_COUPON.value
        )
        self.assertEqual(pay_history1.payment_account, "")
        self.assertEqual(pay_history1.app_service_id, app_service1.id)
        self.assertEqual(pay_history1.instance_id, "")
        self.assertEqual(pay_history1.app_id, settings.PAYMENT_BALANCE["app_id"])
        self.assertEqual(pay_history1.subject, "安全扫描计费")
