from decimal import Decimal
from urllib import parse

from django.urls import reverse
from django.utils import timezone

from utils.model import OwnerType
from utils.test import get_or_create_service, get_or_create_user, MyAPITestCase
from servers.models import ServiceConfig
from vo.models import VirtualOrganization, VoMember
from bill.models import PaymentHistory, CashCouponPaymentHistory


class PaymentHistoryTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.service = get_or_create_service()
        self.service.pay_app_service_id = 'app_service1_id'
        self.service.save(update_fields=['pay_app_service_id'])
        self.service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False, pay_app_service_id='app_service2'
        )
        self.service2.save(force_insert=True)
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save()

    def init_payment_history_data(self):
        time_now = timezone.now()
        history1 = PaymentHistory(
            subject='subject1',
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            payable_amounts=Decimal('1.11'),
            amounts=Decimal('-1.11'),
            app_service_id=self.service.pay_app_service_id,
            instance_id='',
            creation_time=time_now.replace(year=2022, month=2, day=8),
            payment_time=time_now.replace(year=2022, month=2, day=8),
            status=PaymentHistory.Status.SUCCESS.value
        )
        history1.save(force_insert=True)

        history2 = PaymentHistory(
            subject='subject2',
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            payable_amounts=Decimal('2.22'),
            amounts=Decimal('-2.22'),
            app_service_id=self.service.pay_app_service_id,
            instance_id='',
            creation_time=time_now.replace(year=2022, month=3, day=7),
            payment_time=time_now.replace(year=2022, month=3, day=7),
            status=PaymentHistory.Status.SUCCESS.value
        )
        history2.save(force_insert=True)

        history3 = PaymentHistory(
            subject='subject3',
            payment_account=self.vo.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.vo.id,
            payer_name=self.vo.name,
            payer_type=OwnerType.VO.value,
            payable_amounts=Decimal('3.33'),
            amounts=Decimal('-3.33'),
            app_service_id=self.service.pay_app_service_id,
            instance_id='',
            creation_time=time_now.replace(year=2022, month=3, day=8),
            payment_time=time_now.replace(year=2022, month=3, day=8),
            status=PaymentHistory.Status.SUCCESS.value
        )
        history3.save(force_insert=True)

        history4 = PaymentHistory(
            subject='subject4',
            payment_account=self.vo.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.vo.id,
            payer_name=self.vo.name,
            payer_type=OwnerType.VO.value,
            payable_amounts=Decimal('4.44'),
            amounts=Decimal('-4.44'),
            app_service_id=self.service.pay_app_service_id,
            instance_id='',
            creation_time=time_now.replace(year=2021, month=4, day=8),
            payment_time=time_now.replace(year=2021, month=4, day=8),
            status=PaymentHistory.Status.SUCCESS.value
        )
        history4.save(force_insert=True)

        history5 = PaymentHistory(
            subject='subject5',
            payment_account=self.vo.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.vo.id,
            payer_name=self.vo.name,
            payer_type=OwnerType.VO.value,
            payable_amounts=Decimal('5.55'),
            amounts=Decimal('-5.55'),
            app_service_id=self.service2.pay_app_service_id,
            instance_id='',
            creation_time=time_now.replace(year=2022, month=1, day=8),
            payment_time=time_now.replace(year=2022, month=1, day=8),
            status=PaymentHistory.Status.WAIT.value
        )
        history5.save(force_insert=True)

        history6 = PaymentHistory(
            subject='subject6',
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            amounts=Decimal('-6.66'),
            app_service_id=self.service2.pay_app_service_id,
            instance_id='',
            creation_time=time_now.replace(year=2022, month=3, day=9),
            payment_time=time_now.replace(year=2022, month=3, day=9),
            status=PaymentHistory.Status.CLOSED.value
        )
        history6.save(force_insert=True)

        history7 = PaymentHistory(
            subject='subject7',
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            payable_amounts=Decimal('7.77'),
            amounts=Decimal('-7.77'),
            app_service_id='',
            instance_id='',
            creation_time=time_now.replace(year=2022, month=1, day=1),
            payment_time=time_now.replace(year=2022, month=1, day=1),
            status=PaymentHistory.Status.ERROR.value
        )
        history7.save(force_insert=True)
        return [history1, history2, history3, history4, history5, history6, history7]

    def test_list_payment_history(self):
        self.init_payment_history_data()

        # --------------list user-------------
        # list user payment history, default current month
        base_url = reverse('wallet-api:payment-history-list')
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
            "payer_type", "amounts", "coupon_amount",
            "payment_time", "remark", "order_id", "subject", "app_service_id", "app_id",
            "status", 'status_desc', 'creation_time', 'payable_amounts'
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

        # query 'status'
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'status': PaymentHistory.Status.SUCCESS.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'status': PaymentHistory.Status.ERROR.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-7.77')

        # param service1_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'app_service_id': self.service.pay_app_service_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)

        # param service2_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'app_service_id': self.service2.pay_app_service_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-6.66')

        # --------------list vo-------------
        # list vo payment history
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z', 'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)

        # query 'status'
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'status': PaymentHistory.Status.SUCCESS.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-3.33')
        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'status': PaymentHistory.Status.WAIT.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-5.55')

        # param service1_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'app_service_id': self.service.pay_app_service_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)

        # param service2_id
        query = parse.urlencode(query={
            'time_start': '2022-02-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'app_service_id': self.service2.pay_app_service_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={
            'time_start': '2022-01-01T00:00:00Z', 'time_end': '2022-04-01T00:00:00Z',
            'vo_id': self.vo.id, 'app_service_id': self.service2.pay_app_service_id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['amounts'], '-5.55')

    def test_detail_payment_history(self):
        history1 = PaymentHistory(
            subject='subject1',
            payment_account=self.user.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE_COUPON.value,
            executor='test',
            payer_id=self.user.id,
            payer_name=self.user.username,
            payer_type=OwnerType.USER.value,
            payable_amounts=Decimal(0),
            amounts=Decimal('-1.11'),
            app_service_id=self.service.pay_app_service_id,
            instance_id='',
            creation_time=timezone.now(),
            payment_time=timezone.now()
        )
        history1.save(force_insert=True)

        cph = CashCouponPaymentHistory(
            payment_history_id=history1.id,
            cash_coupon_id=None,
            amounts=Decimal('-1.00'),
            before_payment=Decimal('6'),
            after_payment=Decimal('5')
        )
        cph.save(force_insert=True)

        # user payment history detail
        base_url = reverse('wallet-api:payment-history-detail', kwargs={'id': history1.id})
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn([
            "id", "payment_method", "executor", "payer_id", "payer_name",
            "payer_type", "amounts", "coupon_amount",
            "payment_time", "remark", "order_id",
            "subject", "app_service_id", "app_id", "coupon_historys",
            "status", 'status_desc', 'creation_time', 'payable_amounts'
        ], r.data)
        self.assertEqual(r.data['amounts'], '-1.11')
        self.assertIsInstance(r.data['coupon_historys'], list)
        self.assertEqual(len(r.data['coupon_historys']), 1)
        self.assertKeysIn([
            "cash_coupon_id", "amounts", "before_payment", "after_payment", "creation_time"
        ], r.data['coupon_historys'][0])

        # ----- vo ------
        history_vo = PaymentHistory(
            subject='subject2',
            payment_account=self.vo.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE.value,
            executor='test',
            payer_id=self.vo.id,
            payer_name=self.vo.name,
            payer_type='',
            payable_amounts=Decimal('6.88'),
            amounts=Decimal('-6.88'),
            app_service_id=self.service.pay_app_service_id,
            instance_id='',
            creation_time=timezone.now(),
            payment_time=timezone.now()
        )
        history_vo.save(force_insert=True)
        user2 = get_or_create_user(username='test2')
        self.client.logout()
        self.client.force_login(user2)

        # user payment history detail
        base_url = reverse('wallet-api:payment-history-detail', kwargs={'id': history_vo.id})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=409, code='UnknownOwnPayment', response=response)

        history_vo.payer_type = OwnerType.VO.value
        history_vo.save(update_fields=['payer_type'])

        base_url = reverse('wallet-api:payment-history-detail', kwargs={'id': history_vo.id})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user=user2, vo=self.vo, role=VoMember.Role.MEMBER.value, inviter='').save(force_insert=True)

        base_url = reverse('wallet-api:payment-history-detail', kwargs={'id': history_vo.id})
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn([
            "id", "payment_method", "executor", "payer_id", "payer_name",
            "payer_type", "amounts", "coupon_amount",
            "payment_time", "remark", "order_id",
            "subject", "app_service_id", "app_id", "coupon_historys",
            "status", 'status_desc', 'creation_time', 'payable_amounts'
        ], r.data)
        self.assertEqual(r.data['amounts'], '-6.88')
        self.assertIsInstance(r.data['coupon_historys'], list)
        self.assertEqual(len(r.data['coupon_historys']), 0)
