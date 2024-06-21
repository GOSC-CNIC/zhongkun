from decimal import Decimal
from urllib import parse
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.decimal_utils import quantize_10_2
from utils.test import MyAPITestCase, get_or_create_user
from utils.model import PayType
from apps.servers.tests import create_server_metadata
from apps.servers.managers import ServerSnapshotManager
from apps.servers.models import ServerSnapshot
from apps.order.models import Order
from apps.order.tests import create_price


class PriceTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.price = create_price()

    def test_server_snapshot(self):
        # ------ server ---------
        now_time = dj_timezone.now()
        expiration_time = now_time + timedelta(days=10)
        server = create_server_metadata(
            service=None, user=self.user, vo_id=None, pay_type=PayType.PREPAID.value,
            expiration_time=expiration_time, public_ip=True, vcpus=2, ram=2, disk_size=0
        )

        price = self.price
        prepaid_discount = Decimal.from_float(price.prepaid_discount/100)
        base_url = reverse('servers-api:snapshot-describe-price-list')

        # period
        query = parse.urlencode(query={
            'server_id': 'test', 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={
            'server_id': 'test', 'period': 0, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={
            'server_id': 'test', 'period': 'test', 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # period_unit
        query = parse.urlencode(query={
            'server_id': 'test', 'period': 1
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={
            'server_id': 'test', 'period': 1, 'period_unit': 'tes'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # server_id
        query = parse.urlencode(query={
            'period': 1, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={
            'server_id': 'test', 'period': 1, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # ok
        query = parse.urlencode(query={
            'server_id': server.id, 'period': 1, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        server.disk_size = 100
        server.save(update_fields=['disk_size'])
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['price'], response.data)
        self.assertKeysIn(['original', 'trade'], response.data['price'])
        original_p = price.vm_disk_snap * 100
        original_p *= 24
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        query = parse.urlencode(query={
            'server_id': server.id, 'period': 128, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        original_p = price.vm_disk_snap * 100
        original_p *= 24 * 128
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        query = parse.urlencode(query={
            'server_id': server.id, 'period': 1, 'period_unit': Order.PeriodUnit.MONTH.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        original_p = price.vm_disk_snap * 100
        original_p *= 24 * 30
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        server.disk_size = 200
        server.save(update_fields=['disk_size'])
        query = parse.urlencode(query={
            'server_id': server.id, 'period': 12, 'period_unit': Order.PeriodUnit.MONTH.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        original_p = price.vm_disk_snap * 200
        original_p *= 24 * 30 * 12
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

    def test_renew_snapshot(self):
        # ------ server ---------
        now_time = dj_timezone.now()
        expiration_time = now_time + timedelta(days=10)
        server1 = create_server_metadata(
            service=None, user=self.user, vo_id=None, pay_type=PayType.PREPAID.value,
            expiration_time=expiration_time, public_ip=True, vcpus=2, ram=2, disk_size=0
        )
        snapshot1 = ServerSnapshotManager.create_snapshot_metadata(
            name='name1', size_dib=0, remarks='snapshot1 test', instance_id='11',
            creation_time=dj_timezone.now(), expiration_time=dj_timezone.now() - timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user, vo=None,
            server=server1, service=server1.service
        )

        price = self.price
        prepaid_discount = Decimal.from_float(price.prepaid_discount/100)
        base_url = reverse('servers-api:snapshot-describe-price-renew')

        # period
        query = parse.urlencode(query={
            'snapshot_id': 'test', 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={
            'snapshot_id': 'test', 'period': 0, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={
            'snapshot_id': 'test', 'period': 'test', 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # period_unit
        query = parse.urlencode(query={
            'snapshot_id': 'test', 'period': 1
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={
            'snapshot_id': 'test', 'period': 1, 'period_unit': 'tes'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # snapshot_id
        query = parse.urlencode(query={
            'period': 1, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={
            'snapshot_id': 'test', 'period': 1, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # ok，快照大小未知
        query = parse.urlencode(query={
            'snapshot_id': snapshot1.id, 'period': 1, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        snapshot1.size = 66
        snapshot1.save(update_fields=['size'])
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['price'], response.data)
        self.assertKeysIn(['original', 'trade'], response.data['price'])
        original_p = price.vm_disk_snap * 66
        original_p *= 24
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        query = parse.urlencode(query={
            'snapshot_id': snapshot1.id, 'period': 128, 'period_unit': Order.PeriodUnit.DAY.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        original_p = price.vm_disk_snap * 66
        original_p *= 24 * 128
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        query = parse.urlencode(query={
            'snapshot_id': snapshot1.id, 'period': 1, 'period_unit': Order.PeriodUnit.MONTH.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        original_p = price.vm_disk_snap * 66
        original_p *= 24 * 30
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])

        snapshot1.size = 200
        snapshot1.save(update_fields=['size'])
        query = parse.urlencode(query={
            'snapshot_id': snapshot1.id, 'period': 12, 'period_unit': Order.PeriodUnit.MONTH.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        original_p = price.vm_disk_snap * 200
        original_p *= 24 * 30 * 12
        trade_p = original_p * prepaid_discount
        self.assertEqual(str(quantize_10_2(original_p)), response.data['price']['original'])
        self.assertEqual(str(quantize_10_2(trade_p)), response.data['price']['trade'])
