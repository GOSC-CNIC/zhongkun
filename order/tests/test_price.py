from decimal import Decimal
from urllib import parse
from datetime import timedelta, timezone

from django.urls import reverse
from django.utils import timezone as dj_timezone

from servers.models import Flavor, Disk
from servers.tests.test_disk import create_disk_metadata
from servers.tests import create_server_metadata
from order.models import Price
from order.managers import PriceManager
from utils.decimal_utils import quantize_10_2
from utils.model import PayType
from utils.test import MyAPITestCase, get_or_create_user


utc = timezone.utc


class PriceTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
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
            prepaid_discount=66
        )
        price.save()
        self.price = price
        self.flavor = Flavor(vcpus=2, ram=4)
        self.flavor.save()

    def test_describe_price(self):
        self.describe_price_server()
        self.describe_price_disk()
        self.describe_price_bucket()

    def describe_price_server(self):
        price = self.price
        prepaid_discount = Decimal.from_float(price.prepaid_discount/100)
        base_url = reverse('order-api:describe-price-list')

        # prepaid
        query = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'prepaid',
            'flavor_id': self.flavor.id, 'external_ip': True,
            'system_disk_size': 100
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['price'], response.data)
        self.assertKeysIn(['original', 'trade'], response.data['price'])
        original_p = price.vm_cpu * 2 + price.vm_ram * 4 + price.vm_pub_ip + price.vm_disk * 100
        original_p *= 24
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        # postpaid
        query2 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'postpaid',
            'flavor_id': self.flavor.id, 'external_ip': True,
            'system_disk_size': 100
        })
        response = self.client.get(f'{base_url}?{query2}')
        self.assertEqual(response.status_code, 200)
        original_p2 = price.vm_cpu * 2 + price.vm_ram * 4 + price.vm_pub_ip + price.vm_disk * 100
        original_p2 *= 24
        self.assertEqual(str(quantize_10_2(original_p2)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(original_p2)), response.data['price']['trade'])

        # period
        query3 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'prepaid', 'period': 1,
            'flavor_id': self.flavor.id, 'external_ip': True,
            'system_disk_size': 100
        })
        days = PriceManager.period_month_days(months=1)
        original_p3 = price.vm_cpu * 2 + price.vm_ram * 4 + price.vm_pub_ip + price.vm_disk * 100
        original_p3 = original_p3 * days * 24
        trade_p3 = original_p3 * prepaid_discount
        response = self.client.get(f'{base_url}?{query3}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(quantize_10_2(original_p3)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p3)), response.data['price']['trade'])

        # external_ip
        query4 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'prepaid', 'period': 1,
            'flavor_id': self.flavor.id, 'external_ip': False,
            'system_disk_size': 100
        })
        days = PriceManager.period_month_days(months=1)
        original_p4 = price.vm_cpu * 2 + price.vm_ram * 4 + price.vm_disk * 100
        original_p4 = original_p4 * days * 24
        trade_p4 = original_p4 * prepaid_discount
        response = self.client.get(f'{base_url}?{query4}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(quantize_10_2(original_p4)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p4)), response.data['price']['trade'])

        # system_disk_size
        query5 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'prepaid', 'period': 1,
            'flavor_id': self.flavor.id, 'external_ip': False,
            'system_disk_size': 50
        })
        days = PriceManager.period_month_days(months=1)
        original_p5 = price.vm_cpu * 2 + price.vm_ram * 4 + price.vm_disk * 50
        original_p5 = original_p5 * days * 24
        trade_p5 = original_p5 * prepaid_discount
        response = self.client.get(f'{base_url}?{query5}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(quantize_10_2(original_p5)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p5)), response.data['price']['trade'])

        # flavor_id
        query6 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'postpaid',
            'flavor_id': 'test', 'external_ip': True,
            'system_disk_size': 100
        })
        response = self.client.get(f'{base_url}?{query6}')
        self.assertEqual(response.status_code, 400)

        # postpaid, only flavor_id
        query7 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'postpaid',
            'flavor_id': self.flavor.id
        })
        response = self.client.get(f'{base_url}?{query7}')
        self.assertEqual(response.status_code, 200)
        original_p7 = price.vm_cpu * 2 + price.vm_ram * 4
        original_p7 *= 24
        self.assertEqual(str(quantize_10_2(original_p7)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(original_p7)), response.data['price']['trade'])

        # postpaid, only flavor_id, external_ip
        query8 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'postpaid',
            'flavor_id': self.flavor.id, 'external_ip': True
        })
        response = self.client.get(f'{base_url}?{query8}')
        self.assertEqual(response.status_code, 200)
        original_p8 = price.vm_cpu * 2 + price.vm_ram * 4 + price.vm_pub_ip
        original_p8 *= 24
        self.assertEqual(str(quantize_10_2(original_p8)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(original_p8)), response.data['price']['trade'])

        # prepaid, only flavor_id, external_ip
        query9 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'prepaid',
            'flavor_id': self.flavor.id, 'external_ip': True
        })
        response = self.client.get(f'{base_url}?{query9}')
        self.assertEqual(response.status_code, 200)
        original_p9 = price.vm_cpu * 2 + price.vm_ram * 4 + price.vm_pub_ip
        original_p9 *= 24
        trade_p9 = original_p9 * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p9)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p9)), response.data['price']['trade'])

        # number, prepaid, only flavor_id, external_ip
        query10 = parse.urlencode(query={
            'resource_type': 'vm', 'pay_type': 'prepaid',
            'flavor_id': self.flavor.id, 'external_ip': True, 'number': 3
        })
        response = self.client.get(f'{base_url}?{query10}')
        self.assertEqual(response.status_code, 200)
        original_p10 = price.vm_cpu * 2 + price.vm_ram * 4 + price.vm_pub_ip
        original_p10 = original_p10 * 24 * 3
        trade_p10 = original_p10 * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p10)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p10)), response.data['price']['trade'])

    def describe_price_disk(self):
        price = self.price
        prepaid_discount = Decimal.from_float(price.prepaid_discount/100)
        base_url = reverse('order-api:describe-price-list')

        # prepaid
        query = parse.urlencode(query={
            'resource_type': 'disk', 'pay_type': 'prepaid',
            'data_disk_size': 100
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['price'], response.data)
        self.assertKeysIn(['original', 'trade'], response.data['price'])
        original_p = price.disk_size * 100
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        # postpaid
        query = parse.urlencode(query={
            'resource_type': 'disk', 'pay_type': 'postpaid',
            'data_disk_size': 100
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        original_p = price.disk_size * 100
        trade_p = original_p
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        # prepaid period
        period = 2          # must be 1 - 12
        data_disk_size = 100
        query = parse.urlencode(query={
            'resource_type': 'disk', 'pay_type': 'prepaid', 'period': period,
            'data_disk_size': data_disk_size
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        days = PriceManager.period_month_days(months=period)
        original_p3 = price.disk_size * data_disk_size
        original_p3 = original_p3 * days
        trade_p3 = original_p3 * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p3)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p3)), response.data['price']['trade'])

        # prepaid period number
        period = 2  # must be 1 - 12
        data_disk_size = 100
        query = parse.urlencode(query={
            'resource_type': 'disk', 'pay_type': 'prepaid', 'period': period,
            'data_disk_size': data_disk_size, 'number': 2
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        days = PriceManager.period_month_days(months=period)
        original_p3a = price.disk_size * data_disk_size * 2
        original_p3a = original_p3a * days
        trade_p3a = original_p3a * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p3a)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p3a)), response.data['price']['trade'])

        # postpaid period
        period = 10  # must be 1 - 12
        data_disk_size = 150
        query = parse.urlencode(query={
            'resource_type': 'disk', 'pay_type': 'postpaid', 'period': period,
            'data_disk_size': data_disk_size
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        days = PriceManager.period_month_days(months=period)
        original_p4 = price.disk_size * data_disk_size
        trade_p4 = original_p4 = original_p4 * days
        self.assertEqual(str(quantize_10_2(original_p4)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p4)), response.data['price']['trade'])

        # postpaid period number
        period = 10  # must be 1 - 12
        data_disk_size = 150
        query = parse.urlencode(query={
            'resource_type': 'disk', 'pay_type': 'postpaid', 'period': period,
            'data_disk_size': data_disk_size, 'number': 3
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        days = PriceManager.period_month_days(months=period)
        original_p5 = price.disk_size * data_disk_size * 3
        trade_p5 = original_p5 = original_p5 * days
        self.assertEqual(str(quantize_10_2(original_p5)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p5)), response.data['price']['trade'])

        # 400
        query = parse.urlencode(query={
            'resource_type': 'disk', 'pay_type': 'postpaid', 'period': 2,
            'data_disk_size': -1
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 400)

        query = parse.urlencode(query={
            'resource_type': 'disk', 'pay_type': 'postpaid', 'period': -2,
            'data_disk_size': 100
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 400)

    def describe_price_bucket(self):
        price = self.price
        base_url = reverse('order-api:describe-price-list')

        query = parse.urlencode(query={
            'resource_type': 'bucket'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['price'], response.data)
        self.assertKeysIn(['original', 'trade'], response.data['price'])
        trade_p = original_p = price.obj_size * 24
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        # number
        query = parse.urlencode(query={
            'resource_type': 'bucket', 'number': 3
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['price'], response.data)
        self.assertKeysIn(['original', 'trade'], response.data['price'])
        trade_p = original_p = price.obj_size * 24
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        query = parse.urlencode(query={
            'resource_type': 'test'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 400)

    def test_describe_renewal_price(self):
        price = self.price
        prepaid_discount = Decimal.from_float(price.prepaid_discount / 100)
        base_url = reverse('order-api:describe-price-renewal-price')

        # missing "resource_type"
        query = parse.urlencode(query={
            'instance_id': '', 'period': 1, 'renew_to_time': ''
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingResourceType', response=response)

        # invalid "resource_type"
        query = parse.urlencode(query={
            'resource_type': '', 'instance_id': '', 'period': 1, 'renew_to_time': ''
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidResourceType', response=response)

        # missing "instance_id"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'period': 1, 'renew_to_time': ''
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingInstanceId', response=response)

        # invalid "instance_id"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': '', 'period': 1, 'renew_to_time': ''
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidInstanceId', response=response)

        # conflict "period" and "renew_to_time"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': 'xxx', 'period': 1, 'renew_to_time': ''
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='PeriodConflictRenewToTime', response=response)

        # missing "period" and "renew_to_time"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': 'xxx'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingPeriod', response=response)

        # invalid "period"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': 'xxx', 'period': 'a'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)

        # invalid "renew_to_time"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': 'xxx', 'renew_to_time': ''
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidRenewToTime', response=response)

        # not found "instance"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': 'xxx', 'period': 1
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFoundInstanceId', response=response)

        # ------ server ---------
        now_time = dj_timezone.now()
        expiration_time = now_time + timedelta(days=10)
        renew_to_time = expiration_time + timedelta(days=30)
        server = create_server_metadata(
            service=None, user=self.user, vo_id=None, pay_type=PayType.PREPAID.value,
            expiration_time=expiration_time, public_ip=True, vcpus=2, ram=2, disk_size=100
        )

        # invalid "renew_to_time"
        rtt_utc = now_time.astimezone(tz=utc)
        rtt_utc_str = rtt_utc.isoformat()[0:19] + "Z"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': server.id, 'renew_to_time': rtt_utc_str
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='InvalidRenewToTime', response=response)

        # ok renew_to_time
        renew_to_time_str = renew_to_time.isoformat()[0:19] + "Z"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': server.id, 'renew_to_time': renew_to_time_str
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['original', 'trade'], container=response.data['price'])

        original_p = price.vm_cpu * 2 + price.vm_ram * 2 + price.vm_pub_ip + price.vm_disk * 100
        original_p *= 24 * 30
        trade_p = original_p * prepaid_discount
        self.assertEqual(response.data['price']['original'], str(quantize_10_2(original_p)))
        self.assertEqual(response.data['price']['trade'], str(quantize_10_2(trade_p)))

        # ok period
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': server.id, 'period': 2
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['original', 'trade'], container=response.data['price'])

        original_p = price.vm_cpu * 2 + price.vm_ram * 2 + price.vm_pub_ip + price.vm_disk * 100
        original_p *= 24 * 60
        trade_p = original_p * prepaid_discount
        self.assertEqual(response.data['price']['original'], str(quantize_10_2(original_p)))
        self.assertEqual(response.data['price']['trade'], str(quantize_10_2(trade_p)))

        # ok period, postpaid server
        server.pay_type = PayType.POSTPAID.value
        server.expiration_time = None
        server.save(update_fields=['pay_type', 'expiration_time'])

        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': server.id, 'period': 2
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['original', 'trade'], container=response.data['price'])

        original_p = price.vm_cpu * 2 + price.vm_ram * 2 + price.vm_pub_ip + price.vm_disk * 100
        original_p *= 24 * 60
        trade_p = original_p
        self.assertEqual(response.data['price']['original'], str(quantize_10_2(original_p)))
        self.assertEqual(response.data['price']['trade'], str(quantize_10_2(trade_p)))

        # ok renew_to_time, postpaid server
        renew_to_time_str = renew_to_time.isoformat()[0:19] + "Z"
        query = parse.urlencode(query={
            'resource_type': 'vm', 'instance_id': server.id, 'renew_to_time': renew_to_time_str
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['original', 'trade'], container=response.data['price'])

        original_p = price.vm_cpu * 2 + price.vm_ram * 2 + price.vm_pub_ip + price.vm_disk * 100
        original_p *= 24 * 40
        trade_p = original_p
        self.assertEqual(response.data['price']['original'], str(quantize_10_2(original_p)))
        self.assertEqual(response.data['price']['trade'], str(quantize_10_2(trade_p)))

        # ---- disk ---
        now_time = dj_timezone.now()
        expiration_time = now_time + timedelta(days=10)
        renew_to_time = expiration_time + timedelta(days=30)
        disk1 = create_disk_metadata(
            service_id=None, azone_id='1', disk_size=66, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=now_time, expiration_time=expiration_time, remarks='test', server_id=None
        )

        # ok period
        query = parse.urlencode(query={
            'resource_type': 'disk', 'instance_id': disk1.id, 'period': 2
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['original', 'trade'], container=response.data['price'])

        original_p = price.disk_size * 66 * 60
        trade_p = original_p * prepaid_discount
        self.assertEqual(response.data['price']['original'], str(quantize_10_2(original_p)))
        self.assertEqual(response.data['price']['trade'], str(quantize_10_2(trade_p)))

        # ok renew_to_time
        renew_to_time_str = renew_to_time.isoformat()[0:19] + "Z"
        query = parse.urlencode(query={
            'resource_type': 'disk', 'instance_id': disk1.id, 'renew_to_time': renew_to_time_str
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['original', 'trade'], container=response.data['price'])

        original_p = price.disk_size * 66 * 30
        trade_p = original_p * prepaid_discount
        self.assertEqual(response.data['price']['original'], str(quantize_10_2(original_p)))
        self.assertEqual(response.data['price']['trade'], str(quantize_10_2(trade_p)))
