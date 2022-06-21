from decimal import Decimal
from urllib import parse

from django.urls import reverse
from django.utils import timezone

from utils.model import OwnerType
from utils.test import get_or_create_service
from service.models import ServiceConfig
from vo.models import VirtualOrganization
from bill.models import PaymentHistory
from order.models import ResourceType
from . import set_auth_header, MyAPITestCase


class PaymentHistoryTests(MyAPITestCase):
    def setUp(self):
        self.user = set_auth_header(self)
        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='test2', data_center_id=self.service.data_center_id, endpoint_url='test2', username='', password='',
            need_vpn=False
        )
        self.service2.save(force_insert=True)
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save()

    def init_payment_history_data(self):
        time_now = timezone.now()
        history1 = PaymentHistory(
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            amounts=Decimal('-1.11'),
            before_payment=Decimal(0),
            after_payment=Decimal(0),
            type=PaymentHistory.Type.PAYMENT.value,
            resource_type=ResourceType.VM.value,
            service_id=self.service.id,
            instance_id=''
        )
        history1.save(force_insert=True)
        history1.payment_time = time_now.replace(year=2022, month=2, day=8)
        history1.save(update_fields=['payment_time'])

        history2 = PaymentHistory(
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            amounts=Decimal('-2.22'),
            before_payment=Decimal(0),
            after_payment=Decimal(0),
            type=PaymentHistory.Type.PAYMENT.value,
            resource_type=ResourceType.DISK.value,
            service_id=self.service.id,
            instance_id=''
        )
        history2.save(force_insert=True)
        history2.payment_time = time_now.replace(year=2022, month=3, day=7)
        history2.save(update_fields=['payment_time'])

        history3 = PaymentHistory(
            payment_account=self.vo.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.vo.id,
            payer_name=self.vo.name,
            payer_type=OwnerType.VO.value,
            amounts=Decimal('-3.33'),
            before_payment=Decimal(0),
            after_payment=Decimal(0),
            type=PaymentHistory.Type.PAYMENT.value,
            resource_type=ResourceType.VM.value,
            service_id=self.service.id,
            instance_id=''
        )
        history3.save(force_insert=True)
        history3.payment_time = time_now.replace(year=2022, month=3, day=8)
        history3.save(update_fields=['payment_time'])

        history4 = PaymentHistory(
            payment_account=self.vo.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.vo.id,
            payer_name=self.vo.name,
            payer_type=OwnerType.VO.value,
            amounts=Decimal('-4.44'),
            before_payment=Decimal(0),
            after_payment=Decimal(0),
            type=PaymentHistory.Type.PAYMENT.value,
            resource_type=ResourceType.VM.value,
            service_id=self.service.id,
            instance_id=''
        )
        history4.save(force_insert=True)
        history4.payment_time = time_now.replace(year=2021, month=4, day=8)
        history4.save(update_fields=['payment_time'])

        history5 = PaymentHistory(
            payment_account=self.vo.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.vo.id,
            payer_name=self.vo.name,
            payer_type=OwnerType.VO.value,
            amounts=Decimal('-5.55'),
            before_payment=Decimal(0),
            after_payment=Decimal(0),
            type=PaymentHistory.Type.REFUND.value,
            resource_type=ResourceType.DISK.value,
            service_id=self.service2.id,
            instance_id=''
        )
        history5.save(force_insert=True)
        history5.payment_time = time_now.replace(year=2022, month=1, day=8)
        history5.save(update_fields=['payment_time'])

        history6 = PaymentHistory(
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            amounts=Decimal('-6.66'),
            before_payment=Decimal(0),
            after_payment=Decimal(0),
            type=PaymentHistory.Type.PAYMENT.value,
            resource_type=ResourceType.DISK.value,
            service_id=self.service2.id,
            instance_id=''
        )
        history6.save(force_insert=True)
        history6.payment_time = time_now.replace(year=2022, month=3, day=9)
        history6.save(update_fields=['payment_time'])

        history7 = PaymentHistory(
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            amounts=Decimal('7.77'),
            before_payment=Decimal(0),
            after_payment=Decimal(0),
            type=PaymentHistory.Type.RECHARGE.value,
            resource_type='',
            service_id='',
            instance_id=''
        )
        history7.save(force_insert=True)
        history7.payment_time = time_now.replace(year=2022, month=1, day=1)
        history7.save(update_fields=['payment_time'])
        return [history1, history2, history3, history4, history5, history6, history7]

    def test_list_payment_history(self):
        self.init_payment_history_data()

        # --------------list user-------------
        # list user payment history, default current month
        base_url = reverse('api:payment-history-list')
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["has_next", "marker", "next_marker", "page_size", "results"], r.data)
        self.assertEqual(len(r.data['results']), 0)

        # list user payment history, date_start - date_end
        query = parse.urlencode(query={
            'time_start': '2022-03-01T00:00:00Z', 'time_end': '2022-04-01T00:00:01Z'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn([
            "id", "payment_method", "executor", "payer_id", "payer_name",
            "payer_type", "amounts", "before_payment", "after_payment",
            "payment_time", "type", "remark", "order_id",
            "resource_type", "service_id", "instance_id"
        ], r.data['results'][0])

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

        # query 'payment_type'
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'payment_type': PaymentHistory.Type.PAYMENT.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 3)
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'payment_type': PaymentHistory.Type.RECHARGE.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '7.77')

        # query 'resource_type'
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'resource_type': ResourceType.VM.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-1.11')
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'resource_type': ResourceType.DISK.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['amounts'], '-6.66')
        self.assertEqual(r.data['results'][1]['amounts'], '-2.22')

        # --------------list vo-------------
        # list vo payment history
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)

        # query 'payment_type'
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'payment_type': PaymentHistory.Type.PAYMENT.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'payment_type': PaymentHistory.Type.REFUND.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-5.55')

        # query 'resource_type'
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'resource_type': ResourceType.VM.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-5.55')

        # -----------------service admin-------------------
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 0)

        # service admin, no permission service
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)

        # service admin, has permission service
        self.service.users.add(self.user)
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 3)

        # service admin, list user payment history
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'user_id': self.user.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['payer_id'], self.user.id)
        self.assertEqual(r.data['results'][0]['payer_type'], OwnerType.USER.value)

        # service admin, list vo payment history
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'as-admin': '',
            'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['payer_id'], self.vo.id)
        self.assertEqual(r.data['results'][0]['payer_type'], OwnerType.VO.value)

        # service admin, list vo payment history, param "vo_id" and "user_id" togethor
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'as-admin': '',
            'vo_id': self.vo.id, 'user_id': self.user.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # service admin, no permission service2
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)

        self.service.users.remove(self.user)

        # --------federal admin-----------
        # federal admin， list all
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 6)

        # list all, query 'payment_type'
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'as-admin': '',
            'payment_type': PaymentHistory.Type.PAYMENT.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 4)
        self.assertEqual(r.data['results'][0]['amounts'], '-6.66')
        self.assertEqual(r.data['results'][1]['amounts'], '-3.33')
        self.assertEqual(r.data['results'][2]['amounts'], '-2.22')
        self.assertEqual(r.data['results'][3]['amounts'], '-1.11')

        # federal admin, service_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 3)

        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-6.66')

        # federal admin, user_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'user_id': self.user.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['payer_type'], OwnerType.USER.value)

        # federal admin, user_id, service_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'user_id': self.user.id,
            'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)

        # federal admin, vo_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')
        self.assertEqual(r.data['results'][1]['amounts'], '-5.55')

        # query vo_id, payment_type
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'vo_id': self.vo.id, 'payment_type': PaymentHistory.Type.PAYMENT.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'as-admin': '', 'vo_id': self.vo.id, 'payment_type': PaymentHistory.Type.RECHARGE.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 0)
