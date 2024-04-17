from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from utils.time import datetime_add_months
from utils.decimal_utils import quantize_10_2
from utils.model import ResourceType, OwnerType, PayType
from apps.order.models import Price, Order, Resource
from apps.order.managers import PriceManager, OrderManager
from apps.order.managers.instance_configs import ScanConfig


class TimeTests(TestCase):
    def test_datetime_add_months(self):
        dt = timezone.now()
        dt = dt.replace(year=2022, month=3, day=15)
        for i in range(1, 20):
            t = datetime_add_months(dt=dt, months=i)
            if 1 <= i <= 9:
                self.assertEqual(t.year, 2022)
                self.assertEqual(t.month, 3 + i)
            elif 10 <= i <= 20:
                self.assertEqual(t.year, 2023)
                self.assertEqual(t.month, 3 + i - 12)


class PriceManagerTests(TestCase):
    def setUp(self):
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
            scan_host=Decimal('111.11'),
            scan_web=Decimal('222.22'),
            prepaid_discount=66
        )
        price.save()
        self.price = price

    @staticmethod
    def _disk_day_price(price, size_gib: int, is_prepaid: bool):
        day_p = price.disk_size * Decimal(size_gib)
        if is_prepaid:
            day_p = day_p * Decimal.from_float(price.prepaid_discount/100)

        return day_p

    def _disk_price_months_test(self, months, is_prepaid: bool):
        size_gib = 50
        price = self.price
        disk_size_day = price.disk_size.__float__()
        # days = days_after_months(timezone.now(), months=months)
        days = PriceManager.period_month_days(months)
        op_months = disk_size_day * days * size_gib
        if is_prepaid:
            tp_months = op_months * price.prepaid_discount / 100
        else:
            tp_months = op_months

        original_price, trade_price = PriceManager().describe_disk_price(
            size_gib=size_gib, period=months, is_prepaid=is_prepaid, days=0)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(Decimal(f'{op_months:.2f}')),
                         msg=f'months={months}')
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(Decimal(f'{tp_months:.2f}')),
                         msg=f'months={months}')

    def test_disk_price(self):
        price = self.price
        pm = PriceManager()

        # one day prepaid
        size_gib = 0
        original_price, trade_price = pm.describe_disk_price(size_gib=size_gib, is_prepaid=True, period=0, days=1)
        tp = self._disk_day_price(price=price, size_gib=size_gib, is_prepaid=True)
        op = self._disk_day_price(price=price, size_gib=size_gib, is_prepaid=False)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(Decimal(0)))
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(Decimal(0)))
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(op))
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(tp))

        size_gib = 50
        original_price, trade_price = pm.describe_disk_price(size_gib=size_gib, is_prepaid=True, period=0, days=1)
        tp = self._disk_day_price(price=price, size_gib=size_gib, is_prepaid=True)
        op = self._disk_day_price(price=price, size_gib=size_gib, is_prepaid=False)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(op))
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(tp))

        size_gib = 150
        original_price, trade_price = pm.describe_disk_price(size_gib=size_gib, is_prepaid=True, period=0, days=1)
        tp = self._disk_day_price(price=price, size_gib=size_gib, is_prepaid=True)
        op = self._disk_day_price(price=price, size_gib=size_gib, is_prepaid=False)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(op))
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(tp))

        # one day postpaid
        original_price, trade_price = pm.describe_disk_price(size_gib=50, is_prepaid=False, period=0, days=1)
        op = self._disk_day_price(price=price, size_gib=50, is_prepaid=False)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(op))
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(op))

        original_price, trade_price = pm.describe_disk_price(size_gib=150, is_prepaid=False, period=0, days=1)
        op = self._disk_day_price(price=price, size_gib=150, is_prepaid=False)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(op))
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(op))

        for i in range(1, 36):
            self._disk_price_months_test(i, is_prepaid=bool(i % 3))

    @staticmethod
    def _server_day_price(price: Price, ram_mib, cpu, disk_gib, public_ip, is_prepaid: bool) -> Decimal:
        p_ram = price.vm_ram * Decimal.from_float(ram_mib / 1024)
        p_cpu = price.vm_cpu * cpu
        p_disk = price.vm_disk * disk_gib
        p = p_ram + p_cpu + p_disk
        if public_ip:
            p += price.vm_pub_ip

        if is_prepaid:
            p = p * Decimal.from_float(price.prepaid_discount / 100)

        return p * 24

    def _server_day_price_test(self, price: Price, ram_mib, cpu, disk_gib, public_ip, is_prepaid: bool):
        pm = PriceManager()
        original_price, trade_price = pm.describe_server_price(
            ram_mib=ram_mib, cpu=cpu, disk_gib=disk_gib, public_ip=public_ip, is_prepaid=is_prepaid, period=0, days=1)
        op = self._server_day_price(
            price=price, ram_mib=ram_mib, cpu=cpu, disk_gib=disk_gib, public_ip=public_ip, is_prepaid=False)

        if is_prepaid:
            tp = self._server_day_price(
                price=price, ram_mib=ram_mib, cpu=cpu, disk_gib=disk_gib, public_ip=public_ip, is_prepaid=True)
        else:
            tp = op
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(op),
                         msg=f'original_price, ram_min={ram_mib}, public_ip={public_ip}')
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(tp),
                         msg=f'trade_price, ram_min={ram_mib}, public_ip={public_ip}')

    def _server_prepaid_months_price_test(self, price: Price, ram_mib, cpu, disk_gib, public_ip, months: int,
                                          is_prepaid: bool):
        pm = PriceManager()
        original_price, trade_price = pm.describe_server_price(
            ram_mib=ram_mib, cpu=cpu, disk_gib=disk_gib, public_ip=public_ip, period=months, days=0,
            is_prepaid=is_prepaid)
        p_day = self._server_day_price(
            price=price, ram_mib=ram_mib, cpu=cpu, disk_gib=disk_gib, public_ip=public_ip, is_prepaid=False)
        # days = days_after_months(dt=timezone.now(), months=months)
        days = PriceManager.period_month_days(months)
        op_months = p_day * days
        if is_prepaid:
            tp_months = op_months * Decimal.from_float(price.prepaid_discount / 100)
        else:
            tp_months = op_months
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(op_months), msg=f'months={months}')
        self.assertEqual(quantize_10_2(trade_price), quantize_10_2(tp_months), msg=f'months={months}')

    def test_server_price(self):
        price = self.price
        self._server_day_price_test(price=price, ram_mib=1024, cpu=2, disk_gib=50, public_ip=True, is_prepaid=True)
        self._server_day_price_test(price=price, ram_mib=1024, cpu=2, disk_gib=50, public_ip=True, is_prepaid=False)
        self._server_day_price_test(price=price, ram_mib=1024, cpu=2, disk_gib=50, public_ip=False, is_prepaid=True)
        self._server_day_price_test(price=price, ram_mib=1024, cpu=2, disk_gib=50, public_ip=False, is_prepaid=False)
        self._server_day_price_test(price=price, ram_mib=4096, cpu=3, disk_gib=150, public_ip=False, is_prepaid=True)
        self._server_day_price_test(price=price, ram_mib=4096, cpu=3, disk_gib=150, public_ip=False, is_prepaid=False)
        self._server_day_price_test(price=price, ram_mib=4096, cpu=3, disk_gib=150, public_ip=True, is_prepaid=True)
        self._server_day_price_test(price=price, ram_mib=4096, cpu=3, disk_gib=150, public_ip=True, is_prepaid=False)
        self._server_day_price_test(price=price, ram_mib=500, cpu=3, disk_gib=0, public_ip=True, is_prepaid=False)
        self._server_day_price_test(price=price, ram_mib=0, cpu=0, disk_gib=150, public_ip=True, is_prepaid=True)

        for i in range(1, 36):
            self._server_prepaid_months_price_test(
                price=price, ram_mib=0, cpu=3, disk_gib=0, public_ip=False, months=i, is_prepaid=bool(i % 3))
            self._server_prepaid_months_price_test(
                price=price, ram_mib=1024, cpu=2, disk_gib=50, public_ip=True, months=i, is_prepaid=bool(i % 3))
            self._server_prepaid_months_price_test(
                price=price, ram_mib=4096, cpu=3, disk_gib=150, public_ip=False, months=i, is_prepaid=bool(i % 3))

    def test_scan_price(self):
        pm = PriceManager()
        original_price, trade_price = pm.describe_scan_price(has_web=True, has_host=True)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(self.price.scan_web + self.price.scan_host))
        original_price, trade_price = pm.describe_scan_price(has_web=True, has_host=False)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(self.price.scan_web))
        original_price, trade_price = pm.describe_scan_price(has_web=False, has_host=True)
        self.assertEqual(quantize_10_2(original_price), quantize_10_2(self.price.scan_host))


class OrderManagerTests(TestCase):
    def setUp(self):
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
            scan_host=Decimal('111.11'),
            scan_web=Decimal('222.22'),
            prepaid_discount=66
        )
        price.save()
        self.price = price

    def test_create(self):
        # scan
        scan_config = ScanConfig(
            name='测试 scan，host and web', host_addr=' 10.8.8.6', web_url='https://test.cn ', remark='test remark')
        scan_order, ress = OrderManager().create_scan_order(
            service_id='scan_service_id',
            service_name='scan_service_name',
            pay_app_service_id='scan_pay_app_service_id',
            instance_config=scan_config,
            user_id='user_id',
            username='username'
        )
        scan_order = Order.objects.get(id=scan_order.id)
        resources = Resource.objects.filter(order_id=scan_order.id).all()
        resources = list(resources)
        self.assertEqual(scan_order.order_type, Order.OrderType.NEW.value)
        self.assertEqual(scan_order.resource_type, ResourceType.SCAN.value)
        self.assertEqual(scan_order.number, 1)
        self.assertEqual(scan_order.status, Order.Status.UNPAID.value)
        self.assertEqual(scan_order.period, 0)
        self.assertEqual(scan_order.pay_type, PayType.PREPAID.value)
        self.assertEqual(scan_order.user_id, 'user_id')
        self.assertEqual(scan_order.username, 'username')
        self.assertEqual(scan_order.owner_type, OwnerType.USER.value)
        self.assertEqual(scan_order.app_service_id, 'scan_pay_app_service_id')
        self.assertEqual(scan_order.service_id, 'scan_service_id')
        self.assertEqual(scan_order.service_name, 'scan_service_name')
        self.assertEqual(scan_order.trading_status, Order.TradingStatus.OPENING.value)
        self.assertEqual(scan_order.total_amount, Decimal('333.33'))
        self.assertEqual(scan_order.payable_amount, quantize_10_2(Decimal('333.33') * Decimal('0.66')))
        sconfig = ScanConfig.from_dict(scan_order.instance_config)
        self.assertEqual(sconfig.web_url, 'https://test.cn')
        self.assertEqual(sconfig.host_addr, '10.8.8.6')
        self.assertEqual(sconfig.name, '测试 scan，host and web')

        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].instance_remark, 'test remark')

        scan_config = ScanConfig(
            name='测试 scan，host', host_addr='10.8.8.6', web_url=' ', remark='test remark66')
        scan_order, ress = OrderManager().create_scan_order(
            service_id='scan_service_id',
            service_name='scan_service_name',
            pay_app_service_id='scan_pay_app_service_id',
            instance_config=scan_config,
            user_id='user_id',
            username='username'
        )
        scan_order = Order.objects.get(id=scan_order.id)
        resources = Resource.objects.filter(order_id=scan_order.id).all()
        resources = list(resources)
        self.assertEqual(scan_order.order_type, Order.OrderType.NEW.value)
        self.assertEqual(scan_order.resource_type, ResourceType.SCAN.value)
        self.assertEqual(scan_order.number, 1)
        self.assertEqual(scan_order.period, 0)
        self.assertEqual(scan_order.pay_type, PayType.PREPAID.value)
        self.assertEqual(scan_order.user_id, 'user_id')
        self.assertEqual(scan_order.username, 'username')
        self.assertEqual(scan_order.owner_type, OwnerType.USER.value)
        self.assertEqual(scan_order.app_service_id, 'scan_pay_app_service_id')
        self.assertEqual(scan_order.service_id, 'scan_service_id')
        self.assertEqual(scan_order.service_name, 'scan_service_name')
        self.assertEqual(scan_order.trading_status, Order.TradingStatus.OPENING.value)
        self.assertEqual(scan_order.total_amount, Decimal('111.11'))
        self.assertEqual(scan_order.payable_amount, quantize_10_2(Decimal('111.11') * Decimal('0.66')))
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].instance_remark, 'test remark66')

        scan_config = ScanConfig(
            name='测试 scan，web', host_addr=' ', web_url='https://test.cn ', remark='test remark88')
        scan_order, ress = OrderManager().create_scan_order(
            service_id='scan_service_id3',
            service_name='scan_service_name3',
            pay_app_service_id='scan_pay_app_service_id3',
            instance_config=scan_config,
            user_id='user_id3',
            username='username3'
        )
        scan_order = Order.objects.get(id=scan_order.id)
        resources = Resource.objects.filter(order_id=scan_order.id).all()
        resources = list(resources)
        self.assertEqual(scan_order.resource_type, ResourceType.SCAN.value)
        self.assertEqual(scan_order.number, 1)
        self.assertEqual(scan_order.period, 0)
        self.assertEqual(scan_order.pay_type, PayType.PREPAID.value)
        self.assertEqual(scan_order.user_id, 'user_id3')
        self.assertEqual(scan_order.username, 'username3')
        self.assertEqual(scan_order.owner_type, OwnerType.USER.value)
        self.assertEqual(scan_order.app_service_id, 'scan_pay_app_service_id3')
        self.assertEqual(scan_order.service_id, 'scan_service_id3')
        self.assertEqual(scan_order.service_name, 'scan_service_name3')
        self.assertEqual(scan_order.total_amount, Decimal('222.22'))
        self.assertEqual(scan_order.payable_amount, quantize_10_2(Decimal('222.22') * Decimal('0.66')))
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].instance_remark, 'test remark88')
