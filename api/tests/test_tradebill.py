from decimal import Decimal
from urllib import parse

from django.urls import reverse
from django.utils import timezone

from utils.model import OwnerType
from utils.test import get_or_create_service
from service.models import ServiceConfig
from vo.models import VirtualOrganization, VoMember
from bill.models import TransactionBill
from bill.managers.bill import TransactionBillManager
from . import set_auth_header, MyAPITestCase, get_or_create_user


class TradeBillTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='lilei@cnic.cn')
        self.pay_app_service1_id = 'app_service1_id'
        self.pay_app_service2_id = 'app_service2'
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save()

    def init_bill_data(self):
        time_now = timezone.now()
        bill1 = TransactionBillManager.create_transaction_bill(
            subject='subject标题1', account='',
            trade_type=TransactionBill.TradeType.PAYMENT.value,
            trade_id='ss',
            amounts=Decimal('-1.11'),
            coupon_amount=Decimal('0'),
            after_balance=Decimal('1'),
            owner_type=OwnerType.USER.value,
            owner_id=self.user.id,
            owner_name=self.user.username,
            app_service_id=self.pay_app_service1_id, app_id='',
            remark='发接口',
            creation_time=time_now.replace(year=2022, month=2, day=8)
        )
        bill2 = TransactionBillManager.create_transaction_bill(
            subject='subject标题2', account='',
            trade_type=TransactionBill.TradeType.PAYMENT.value,
            trade_id='ssff',
            amounts=Decimal('-2.22'),
            coupon_amount=Decimal('0'),
            after_balance=Decimal('2'),
            owner_type=OwnerType.USER.value,
            owner_id=self.user.id,
            owner_name=self.user.username,
            app_service_id=self.pay_app_service1_id, app_id='',
            remark='发了',
            creation_time=time_now.replace(year=2022, month=3, day=7)
        )
        bill3 = TransactionBillManager.create_transaction_bill(
            subject='subject标题3', account='',
            trade_type=TransactionBill.TradeType.PAYMENT.value,
            trade_id='ssff',
            amounts=Decimal('-3.33'),
            coupon_amount=Decimal('0'),
            after_balance=Decimal('3'),
            owner_type=OwnerType.VO.value,
            owner_id=self.vo.id,
            owner_name=self.vo.name,
            app_service_id=self.pay_app_service1_id, app_id='',
            remark='阿卡',
            creation_time=time_now.replace(year=2022, month=3, day=8)
        )
        bill4 = TransactionBillManager.create_transaction_bill(
            subject='subject标题3', account='',
            trade_type=TransactionBill.TradeType.PAYMENT.value,
            trade_id='ssff',
            amounts=Decimal('-4.44'),
            coupon_amount=Decimal('0'),
            after_balance=Decimal('4'),
            owner_type=OwnerType.VO.value,
            owner_id=self.vo.id,
            owner_name=self.vo.name,
            app_service_id=self.pay_app_service1_id, app_id='',
            remark='i武器',
            creation_time=time_now.replace(year=2022, month=4, day=8)
        )
        bill5 = TransactionBillManager.create_transaction_bill(
            subject='subject标题3', account='',
            trade_type=TransactionBill.TradeType.REFUND.value,
            trade_id='ssff',
            amounts=Decimal('5.55'),
            coupon_amount=Decimal('0'),
            after_balance=Decimal('5'),
            owner_type=OwnerType.VO.value,
            owner_id=self.vo.id,
            owner_name=self.vo.name,
            app_service_id=self.pay_app_service2_id, app_id='',
            remark='还去',
            creation_time=time_now.replace(year=2022, month=1, day=8)
        )
        bill6 = TransactionBillManager.create_transaction_bill(
            subject='subject标题3', account='',
            trade_type=TransactionBill.TradeType.RECHARGE.value,
            trade_id='ssff',
            amounts=Decimal('6.66'),
            coupon_amount=Decimal('0'),
            after_balance=Decimal('6'),
            owner_type=OwnerType.USER.value,
            owner_id=self.user.id,
            owner_name=self.user.username,
            app_service_id=self.pay_app_service2_id, app_id='',
            remark='加进去',
            creation_time=time_now.replace(year=2022, month=3, day=9)
        )

        bill7 = TransactionBillManager.create_transaction_bill(
            subject='subject标题3', account='',
            trade_type=TransactionBill.TradeType.REFUND.value,
            trade_id='ssff',
            amounts=Decimal('7.77'),
            coupon_amount=Decimal('0'),
            after_balance=Decimal('7'),
            owner_type=OwnerType.USER.value,
            owner_id=self.user.id,
            owner_name=self.user.username,
            app_service_id=self.pay_app_service2_id, app_id='',
            remark='飞回去',
            creation_time=time_now.replace(year=2022, month=1, day=1)
        )

        return [bill1, bill2, bill3, bill4, bill5, bill6, bill7]

    def test_list_bills(self):
        bill1, bill2, bill3, bill4, bill5, bill6, bill7 = self.init_bill_data()

        # --------------list user-------------
        base_url = reverse('api:tradebill-list')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # list user payment history, default current month
        self.client.force_login(self.user)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["has_next", "marker", "next_marker", "page_size", "results"], r.data)
        self.assertEqual(len(r.data['results']), 0)

        # list user payment history, date_start - date_end
        query = parse.urlencode(query={
            'time_start': '2022-03-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn([
            "id", "subject", "trade_type", "trade_id", "amounts",
            "coupon_amount", "after_balance", "creation_time",
            "remark", "owner_id", "owner_name", "owner_type", "app_service_id"
        ], r.data['results'][0])
        self.assertEqual(bill6.amounts, Decimal('6.66'))
        self.assertEqual(bill6.id, r.data['results'][0]['id'])
        self.assertEqual(bill2.id, r.data['results'][1]['id'])

        # list user payment history, invalid time_start
        query = parse.urlencode(query={
            'time_start': '2022-02-30T00:00:00Z'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user payment history, invalid time_end
        query = parse.urlencode(query={
            'time_end': '2022-04-01T00:00:01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user payment history, date_start date_end timedelta less than one year
        query = parse.urlencode(query={
            'time_start': '2021-03-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user payment history, query page_size
        query = parse.urlencode(query={
            'time_start': '2022-03-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'page_size': 2
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.data["has_next"], False)
        self.assertEqual(r.data["page_size"], 2)
        self.assertEqual(r.data['marker'], None)
        self.assertIs(r.data['next_marker'], None)
        self.assertEqual(len(r.data['results']), 2)
        query = parse.urlencode(query={
            'time_start': '2022-03-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'page_size': 1
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.data["has_next"], True)
        self.assertEqual(r.data["page_size"], 1)
        self.assertEqual(r.data['marker'], None)
        self.assertTrue(r.data['next_marker'])
        self.assertEqual(len(r.data['results']), 1)
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'page_size': 4
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.data["has_next"], False)
        self.assertEqual(r.data["page_size"], 4)
        self.assertEqual(r.data['marker'], None)
        self.assertFalse(r.data['next_marker'])
        self.assertEqual(len(r.data['results']), 3)

        # query 'status'
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'trade_type': TransactionBill.TradeType.PAYMENT.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], bill2.id)
        self.assertEqual(r.data['results'][1]['id'], bill1.id)
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'trade_type': TransactionBill.TradeType.REFUND.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '7.77')
        self.assertEqual(r.data['results'][0]['id'], bill7.id)

        # param service1_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'app_service_id': self.pay_app_service1_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], bill2.id)
        self.assertEqual(r.data['results'][1]['id'], bill1.id)

        # param service2_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'app_service_id': self.pay_app_service2_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], bill6.id)
        self.assertEqual(r.data['results'][0]['amounts'], '6.66')

        # --------------list vo-------------
        # list vo payment history
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], bill3.id)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')

        # query 'status'
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'trade_type': TransactionBill.TradeType.PAYMENT.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], bill3.id)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')

        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'trade_type': TransactionBill.TradeType.REFUND.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], bill5.id)
        self.assertEqual(r.data['results'][0]['amounts'], '5.55')

        # param service1_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'app_service_id': self.pay_app_service1_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], bill3.id)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')

        # param service2_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'app_service_id': self.pay_app_service2_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'app_service_id': self.pay_app_service2_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], bill5.id)
        self.assertEqual(r.data['results'][0]['amounts'], '5.55')
