from decimal import Decimal
from ..models import VtScanService
from django.urls import reverse
from bill.models import PayApp, PayAppService
from utils.test import (
    get_or_create_user,
    get_or_create_organization,
    MyAPITestCase,
)


class ScanPriceTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password="password")
        self.user2 = get_or_create_user(username="tom@cnic.cn", password="password")

    def test_price_list(self):
        # NotAuthenticated
        base_url = reverse("scan-api:price-list")
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=401, code="NotAuthenticated", response=r)

        app = PayApp(name="app")
        app.save()
        app = app
        po = get_or_create_organization(name="机构")
        po.save()
        app_service1 = PayAppService(name="scan", app=app, orgnazition=po)
        app_service1.save()

        scanservice = VtScanService(
            name="安全扫描服务配置信息",
            name_en="scan",
            status=VtScanService.Status.ENABLE,
            remark="scan test",
            host_scan_price=Decimal("50.00"),
            web_scan_price=Decimal("100.00"),
            pay_app_service_id=app_service1.id,
        )
        scanservice.save()

        # ok
        self.client.force_login(self.user)
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=["price"], container=r.data)
        self.assertEqual(r.data["price"]["web"], "100.00")
        self.assertEqual(r.data["price"]["host"], "50.00")
