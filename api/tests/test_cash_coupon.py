from decimal import Decimal
from urllib import parse
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from utils.model import OwnerType
from utils.test import get_or_create_service, get_or_create_user
from vo.models import VirtualOrganization, VoMember
from bill.models import CashCoupon, PayAppService, PayApp, PayOrgnazition
from bill.managers import PaymentManager
from . import set_auth_header, MyAPITestCase


class CashCouponTests(MyAPITestCase):
    def setUp(self):
        self.user = set_auth_header(self)
        self.user2 = get_or_create_user(username='user2')
        self.service = get_or_create_service()
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user2
        )
        self.vo.save()

        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        self.app = app
        po = PayOrgnazition(name='机构')
        po.save()
        self.app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service=self.service
        )
        self.app_service1.save()
        self.app_service2 = PayAppService(
            name='service2', app=app, orgnazition=po
        )
        self.app_service2.save()

    def test_draw_cash_coupon(self):
        coupon1 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=timezone.now(),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.WAIT.value
        )
        coupon1.save(force_insert=True)

        coupon2 = CashCoupon(
            face_value=Decimal('88.8'),
            balance=Decimal('88.8'),
            effective_time=timezone.now(),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.WAIT.value
        )
        coupon2.save(force_insert=True)

        base_url = reverse('api:cashcoupon-list')

        # required param "coupon_code"
        query = parse.urlencode(query={'id': coupon1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingCouponCode', response=response)

        query = parse.urlencode(query={'id': coupon1.id, 'coupon_code': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidCouponCode', response=response)

        # required param "id"
        query = parse.urlencode(query={'coupon_code': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingID', response=response)

        query = parse.urlencode(query={'id': '', 'coupon_code': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidID', response=response)

        # param "vo_id"
        query = parse.urlencode(query={'id': 'test', 'coupon_code': 'test', 'vo_id': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidVoId', response=response)

        # not cash coupon
        query = parse.urlencode(query={'id': 'test', 'coupon_code': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # invalid coupon code
        query = parse.urlencode(query={'id': coupon1.id, 'coupon_code': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='InvalidCouponCode', response=response)

        # ok
        query = parse.urlencode(query={'id': coupon1.id, 'coupon_code': coupon1.coupon_code})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], coupon1.id)
        coupon1.refresh_from_db()
        self.assertEqual(coupon1.user_id, self.user.id)
        self.assertEqual(coupon1.owner_type, OwnerType.USER.value)
        self.assertEqual(coupon1.vo_id, None)
        self.assertEqual(coupon1.status, CashCoupon.Status.AVAILABLE.value)

        # failed if again
        query = parse.urlencode(query={'id': coupon1.id, 'coupon_code': coupon1.coupon_code})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='AlreadyGranted', response=response)

        # not vo
        query = parse.urlencode(query={'id': coupon2.id, 'coupon_code': coupon2.coupon_code, 'vo_id': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 404)

        # no vo permission
        query = parse.urlencode(query={'id': coupon2.id, 'coupon_code': coupon2.coupon_code, 'vo_id': self.vo.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user=self.user, vo=self.vo, role=VoMember.Role.LEADER.value, inviter='').save(force_insert=True)
        query = parse.urlencode(query={'id': coupon2.id, 'coupon_code': coupon2.coupon_code, 'vo_id': self.vo.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], coupon2.id)
        coupon2.refresh_from_db()
        self.assertEqual(coupon2.user_id, self.user.id)
        self.assertEqual(coupon2.owner_type, OwnerType.VO.value)
        self.assertEqual(coupon2.vo_id, self.vo.id)
        self.assertEqual(coupon2.status, CashCoupon.Status.AVAILABLE.value)

    def test_list_cash_coupon(self):
        now_time = timezone.now()
        coupon1 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=1),
            status=CashCoupon.Status.WAIT.value,
            app_service_id=self.app_service1.id
        )
        coupon1.save(force_insert=True)

        coupon2_user = CashCoupon(
            face_value=Decimal('88.8'),
            balance=Decimal('88.8'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=30),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=now_time,
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id
        )
        coupon2_user.save(force_insert=True)
        # 过期
        coupon3_user = CashCoupon(
            face_value=Decimal('188.8'),
            balance=Decimal('168.8'),
            effective_time=now_time - timedelta(days=20),
            expiration_time=now_time - timedelta(days=1),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=now_time,
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service2.id
        )
        coupon3_user.save(force_insert=True)

        coupon4_user2 = CashCoupon(
            face_value=Decimal('288.8'),
            balance=Decimal('258.8'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=30),
            status=CashCoupon.Status.CANCELLED.value,
            granted_time=now_time,
            owner_type=OwnerType.USER.value,
            user=self.user2,
            app_service_id=self.app_service2.id
        )
        coupon4_user2.save(force_insert=True)

        coupon5_vo = CashCoupon(
            face_value=Decimal('388.8'),
            balance=Decimal('358.8'),
            effective_time=now_time - timedelta(days=3),
            expiration_time=now_time + timedelta(days=20),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=now_time,
            owner_type=OwnerType.VO.value,
            user=self.user,
            vo=self.vo,
            app_service_id=self.app_service1.id
        )
        coupon5_vo.save(force_insert=True)

        coupon6_vo = CashCoupon(
            face_value=Decimal('588.8'),
            balance=Decimal('558.8'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=20),
            status=CashCoupon.Status.CANCELLED.value,
            granted_time=now_time,
            owner_type=OwnerType.VO.value,
            user=self.user,
            vo=self.vo,
            app_service_id=self.app_service2.id
        )
        coupon6_vo.save(force_insert=True)

        base_url = reverse('api:cashcoupon-list')

        # list user own coupon
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        results = response.data['results']
        self.assertEqual(len(results), 2)
        self.assertKeysIn([
            "id", "face_value", "creation_time", "effective_time", "expiration_time",
            "balance", "status", "granted_time",
            "owner_type", "app_service", "user", "vo", "activity"], results[0]
        )
        self.assertKeysIn([
            "id", "name", "name_en", "service_id"], results[0]['app_service']
        )
        self.assertEqual(None, results[0]['app_service']['service_id'])
        self.assertEqual(self.service.id, results[1]['app_service']['service_id'])  # 288.8
        self.assert_is_subdict_of(
            {
                'id': coupon3_user.id,
                'face_value': '188.80',
                'balance': '168.80',
                'status': CashCoupon.Status.AVAILABLE.value,
                'owner_type': OwnerType.USER.value,
                'user': {'id': self.user.id, 'username': self.user.username},
                'vo': None
            }, results[0]
        )
        self.assert_is_subdict_of(
            {
                'id': coupon2_user.id,
                'face_value': '88.80',
                'balance': '88.80',
                'status': CashCoupon.Status.AVAILABLE.value,
                'owner_type': OwnerType.USER.value,
                'user': {'id': self.user.id, 'username': self.user.username},
                'vo': None
            }, results[1]
        )

        # list user own coupon, paran "page_size"
        query = parse.urlencode(query={'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # list user own coupon, paran "available"
        query = parse.urlencode(query={'available': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assert_is_subdict_of(
            {
                'id': coupon2_user.id,
                'face_value': '88.80',
                'balance': '88.80',
                'status': CashCoupon.Status.AVAILABLE.value,
                'owner_type': OwnerType.USER.value,
                'user': {'id': self.user.id, 'username': self.user.username},
                'vo': None
            }, response.data['results'][0]
        )

        # list user own coupon, paran "app_service_id"
        query = parse.urlencode(query={'app_service_id': self.app_service1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon2_user.id)
        self.assertEqual(response.data['results'][0]['face_value'], '88.80')

        query = parse.urlencode(query={'app_service_id': self.app_service2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon3_user.id)
        self.assertEqual(response.data['results'][0]['face_value'], '188.80')

        # list user own coupon, paran "app_service_id" "available"
        query = parse.urlencode(query={'app_service_id': self.app_service1.id, 'available': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon2_user.id)
        self.assertEqual(response.data['results'][0]['face_value'], '88.80')

        query = parse.urlencode(query={'app_service_id': self.app_service2.id, 'available': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # list vo coupon
        query = parse.urlencode(query={'vo_id': 'test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        query = parse.urlencode(query={'vo_id': self.vo.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user=self.user, vo=self.vo, role=VoMember.Role.LEADER.value, inviter='').save(force_insert=True)
        query = parse.urlencode(query={'vo_id': self.vo.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 1)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertKeysIn([
            "id", "face_value", "creation_time", "effective_time", "expiration_time",
            "balance", "status", "granted_time",
            "owner_type", "app_service", "user", "vo", "activity"], results[0]
        )
        self.assertKeysIn([
            "id", "name", "name_en", "service_id"], results[0]['app_service']
        )
        self.assertEqual(self.service.id, results[0]['app_service']['service_id'])  # 388.8
        self.assert_is_subdict_of(
            {
                'id': coupon5_vo.id,
                'face_value': '388.80',
                'balance': '358.80',
                'status': CashCoupon.Status.AVAILABLE.value,
                'owner_type': OwnerType.VO.value,
                'user': {'id': self.user.id, 'username': self.user.username},
                'vo': {'id': self.vo.id, 'name': self.vo.name}
            }, results[0]
        )

        # list vo coupon, paran "app_service_id"
        query = parse.urlencode(query={'vo_id': self.vo.id, 'app_service_id': self.app_service1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon5_vo.id)
        self.assertEqual(response.data['results'][0]['face_value'], '388.80')

        query = parse.urlencode(query={'vo_id': self.vo.id, 'app_service_id': self.app_service2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # list user own coupon, paran "app_service_id" "available"
        query = parse.urlencode(query={'vo_id': self.vo.id, 'app_service_id': self.app_service1.id, 'available': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon5_vo.id)
        self.assertEqual(response.data['results'][0]['face_value'], '388.80')

    def test_delete_cash_coupon(self):
        now_time = timezone.now()
        coupon1 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=1),
            status=CashCoupon.Status.WAIT.value
        )
        coupon1.save(force_insert=True)

        coupon2_user = CashCoupon(
            face_value=Decimal('88.8'),
            balance=Decimal('88.8'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=30),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=now_time,
            owner_type=OwnerType.USER.value,
            user=self.user
        )
        coupon2_user.save(force_insert=True)

        coupon3_user = CashCoupon(
            face_value=Decimal('188.8'),
            balance=Decimal('168.8'),
            effective_time=now_time - timedelta(days=20),
            expiration_time=now_time - timedelta(days=1),  # 过期
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=now_time,
            owner_type=OwnerType.USER.value,
            user=self.user
        )
        coupon3_user.save(force_insert=True)

        coupon4_user2 = CashCoupon(
            face_value=Decimal('288.8'),
            balance=Decimal('258.8'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=30),
            status=CashCoupon.Status.CANCELLED.value,
            granted_time=now_time,
            owner_type=OwnerType.USER.value,
            user=self.user2
        )
        coupon4_user2.save(force_insert=True)

        coupon5_vo = CashCoupon(
            face_value=Decimal('388.8'),
            balance=Decimal('358.8'),
            effective_time=now_time - timedelta(days=3),
            expiration_time=now_time + timedelta(days=20),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=now_time,
            owner_type=OwnerType.VO.value,
            user=self.user,
            vo=self.vo
        )
        coupon5_vo.save(force_insert=True)

        # delete status "WAIT" coupon
        url = reverse('api:cashcoupon-detail', kwargs={'id': coupon1.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # need force delete
        url = reverse('api:cashcoupon-detail', kwargs={'id': coupon2_user.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=409, code='BalanceRemain', response=response)
        query = parse.urlencode(query={'force': ''})
        response = self.client.delete(f'{url}?{query}')
        self.assertEqual(response.status_code, 204)
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.status, CashCoupon.Status.DELETED.value)

        # delete expired coupon
        url = reverse('api:cashcoupon-detail', kwargs={'id': coupon3_user.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        coupon3_user.refresh_from_db()
        self.assertEqual(coupon3_user.status, CashCoupon.Status.DELETED.value)

        # delete user2 coupon
        url = reverse('api:cashcoupon-detail', kwargs={'id': coupon4_user2.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        coupon4_user2.refresh_from_db()
        self.assertEqual(coupon4_user2.status, CashCoupon.Status.CANCELLED.value)

        # delete vo coupon
        url = reverse('api:cashcoupon-detail', kwargs={'id': coupon5_vo.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        VoMember(user=self.user, vo=self.vo, role=VoMember.Role.LEADER.value, inviter='').save(force_insert=True)
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=409, code='BalanceRemain', response=response)

        coupon5_vo.balance = Decimal(0)
        coupon5_vo.save(update_fields=['balance'])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        coupon5_vo.refresh_from_db()
        self.assertEqual(coupon5_vo.status, CashCoupon.Status.DELETED.value)

    def test_list_coupon_payments(self):
        now_time = timezone.now()
        coupon1_user = CashCoupon(
            face_value=Decimal('88.8'),
            balance=Decimal('88.8'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=30),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=now_time,
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id
        )
        coupon1_user.save(force_insert=True)

        coupon1_vo = CashCoupon(
            face_value=Decimal('188.8'),
            balance=Decimal('188.8'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=30),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=now_time,
            owner_type=OwnerType.VO.value,
            vo=self.vo,
            app_service_id=self.app_service1.id
        )
        coupon1_vo.save(force_insert=True)

        # ------- list user coupon payment historys -------
        PaymentManager().pay_by_user(
            user_id=self.user.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66.66'),
            executor='test',
            remark='test',
            order_id='123',
            app_service_id=self.app_service1.id,
            resource_type='',
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )

        # list user coupon payment
        base_url = reverse('api:cashcoupon-list-payment', kwargs={'id': coupon1_user.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertKeysIn([
            "cash_coupon_id", "amounts", "before_payment", "after_payment", "creation_time",
            "payment_history"], results[0]
        )
        self.assertKeysIn([
            "id", "subject", "payment_method", "executor", "payer_id", "payer_name", "payer_type", "amounts",
            "coupon_amount", "payment_time", "type", "remark", "order_id", "app_id", "app_service_id"
        ], results[0]["payment_history"])
        self.assertEqual('88.80', results[0]["before_payment"])
        self.assertEqual('-66.66', results[0]["amounts"])
        self.assertEqual('22.14', results[0]["after_payment"])
        self.assertEqual('-66.66', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])

        PaymentManager().pay_by_user(
            user_id=self.user.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66'),
            executor='test',
            remark='test',
            order_id='123',
            app_service_id=self.app_service1.id,
            resource_type='',
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )
        base_url = reverse('api:cashcoupon-list-payment', kwargs={'id': coupon1_user.id})
        response = self.client.get(f"{base_url}?{parse.urlencode(query={'page_size': 1})}")
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['count'], 2)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual('-22.14', results[0]["amounts"])
        self.assertEqual('-22.14', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('-43.86', results[0]["payment_history"]['amounts'])

        # ------- list vo coupon payment historys -------
        PaymentManager().pay_by_vo(
            vo_id=self.vo.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66.66'),
            executor='test',
            remark='test',
            order_id='123',
            app_service_id=self.app_service1.id,
            resource_type='',
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )

        # list vo coupon payment
        base_url = reverse('api:cashcoupon-list-payment', kwargs={'id': coupon1_vo.id})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user=self.user, vo=self.vo, role=VoMember.Role.MEMBER.value, inviter='').save(force_insert=True)

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertKeysIn([
            "cash_coupon_id", "amounts", "before_payment", "after_payment", "creation_time",
            "payment_history"], results[0]
        )
        self.assertKeysIn([
            "id", "subject", "payment_method", "executor", "payer_id", "payer_name", "payer_type", "amounts",
            "coupon_amount", "payment_time", "type", "remark", "order_id", "app_id", "app_service_id"
        ], results[0]["payment_history"])
        self.assertEqual('-66.66', results[0]["amounts"])
        self.assertEqual('188.80', results[0]["before_payment"])
        self.assertEqual('122.14', results[0]["after_payment"])
        self.assertEqual('-66.66', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])

        PaymentManager().pay_by_vo(
            vo_id=self.vo.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66'),
            executor='test',
            remark='test',
            order_id='123',
            app_service_id=self.app_service1.id,
            resource_type='',
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )
        base_url = reverse('api:cashcoupon-list-payment', kwargs={'id': coupon1_vo.id})
        response = self.client.get(f"{base_url}?{parse.urlencode(query={'page_size': 1})}")
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual('-66.00', results[0]["amounts"])
        self.assertEqual('-66.00', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])
