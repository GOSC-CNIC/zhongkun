from decimal import Decimal
from urllib import parse
from datetime import timedelta, datetime

from django.urls import reverse
from django.utils import timezone

from utils.model import OwnerType
from utils.test import (
    get_or_create_service, get_or_create_user, get_or_create_organization,
    MyAPITestCase, MyAPITransactionTestCase
)
from utils.time import utc
from apps.app_vo.models import VirtualOrganization, VoMember
from apps.app_wallet.models import (
    CashCoupon, PayAppService, PayApp, CashCouponActivity, TransactionBill, PaymentHistory,
    CashCouponPaymentHistory, RefundRecord
)
from apps.app_wallet.managers import PaymentManager, CashCouponActivityManager
from apps.app_wallet.handlers.cash_coupon_handler import QueryCouponValidChoices
from core import errors


def to_isoformat(value):
    return value.isoformat(timespec='seconds').split('+')[0] + 'Z'


class CashCouponTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
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
        po = get_or_create_organization(name='机构')
        po.save()
        self.app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service_id=self.service.id,
            category=PayAppService.Category.VMS_SERVER.value
        )
        self.app_service1.save()
        self.app_service2 = PayAppService(
            name='service2', app=app, orgnazition=po, category=PayAppService.Category.VMS_OBJECT.value
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

        base_url = reverse('wallet-api:cashcoupon-list')

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

        # no bind app_service, InvalidCoupon
        query = parse.urlencode(query={'id': coupon1.id, 'coupon_code': coupon1.coupon_code})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='InvalidCoupon', response=response)

        coupon1.app_service_id = self.app_service1.id
        coupon1.save(update_fields=['app_service_id'])

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

        # no bind app_service, InvalidCoupon
        query = parse.urlencode(query={'id': coupon2.id, 'coupon_code': coupon2.coupon_code})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='InvalidCoupon', response=response)

        # only coupon that binded app_server is vms-server can to vo
        coupon2.app_service_id = self.app_service2.id
        coupon2.save(update_fields=['app_service_id'])
        query = parse.urlencode(query={'id': coupon2.id, 'coupon_code': coupon2.coupon_code, 'vo_id': self.vo.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='NotAllowToVo', response=response)

        # ok
        coupon2.app_service_id = self.app_service1.id
        coupon2.save(update_fields=['app_service_id'])
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

        base_url = reverse('wallet-api:cashcoupon-list')

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
            "balance", "status", "granted_time", "issuer", 'use_scope', 'order_id',
            "owner_type", "app_service", "user", "vo", "activity", 'remark'], results[0]
        )
        self.assertKeysIn([
            "id", "name", "name_en", "service_id", "category"], results[0]['app_service']
        )
        self.assertEqual('', results[0]['app_service']['service_id'])     # 188.80
        self.assertEqual(self.service.id, results[1]['app_service']['service_id'])  # 88.80
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

        # list user own coupon, paran "valid"
        query = parse.urlencode(query={'valid': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidValid', response=response)

        query = parse.urlencode(query={'valid': QueryCouponValidChoices.VALID.value})
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

        query = parse.urlencode(query={'valid': QueryCouponValidChoices.EXPIRED.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon3_user.id)

        query = parse.urlencode(query={'valid': QueryCouponValidChoices.NOT_YET.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

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

        # list user own coupon, paran "app_service_id" "valid"
        query = parse.urlencode(query={
            'app_service_id': self.app_service1.id, 'valid': QueryCouponValidChoices.VALID.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon2_user.id)
        self.assertEqual(response.data['results'][0]['face_value'], '88.80')

        query = parse.urlencode(query={
            'app_service_id': self.app_service2.id, 'valid': QueryCouponValidChoices.VALID.value})
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
            "balance", "status", "granted_time", 'use_scope', 'order_id', 'remark',
            "owner_type", "app_service", "user", "vo", "activity"], results[0]
        )
        self.assertKeysIn([
            "id", "name", "name_en", "service_id", "category"], results[0]['app_service']
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

        # list vo coupon, paran "app_service_id" "valid"
        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'app_service_id': self.app_service1.id, 'valid': QueryCouponValidChoices.VALID.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon5_vo.id)
        self.assertEqual(response.data['results'][0]['face_value'], '388.80')

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'app_service_id': self.app_service1.id,
            'valid': QueryCouponValidChoices.EXPIRED.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # invalid paran "app_service_category"
        query = parse.urlencode(query={'app_service_category': 'test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidAppServiceCategory', response=response)

        # list user own coupon, paran "app_service_category"
        query = parse.urlencode(query={'app_service_category': PayAppService.Category.VMS_SERVER.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon2_user.id)
        self.assertEqual(response.data['results'][0]['face_value'], '88.80')

        query = parse.urlencode(query={'app_service_category': PayAppService.Category.VMS_OBJECT.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], coupon3_user.id)
        self.assertEqual(response.data['results'][0]['face_value'], '188.80')

        # list vo coupon, paran "app_service_category"
        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'app_service_category': PayAppService.Category.VMS_SERVER.value})
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
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon1.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # need force delete
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon2_user.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=409, code='BalanceRemain', response=response)
        query = parse.urlencode(query={'force': ''})
        response = self.client.delete(f'{url}?{query}')
        self.assertEqual(response.status_code, 204)
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.status, CashCoupon.Status.DELETED.value)

        # delete expired coupon
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon3_user.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        coupon3_user.refresh_from_db()
        self.assertEqual(coupon3_user.status, CashCoupon.Status.DELETED.value)

        # delete user2 coupon
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon4_user2.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        coupon4_user2.refresh_from_db()
        self.assertEqual(coupon4_user2.status, CashCoupon.Status.CANCELLED.value)

        # delete vo coupon
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon5_vo.id})
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
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )

        # list user coupon payment
        base_url = reverse('wallet-api:cashcoupon-list-payment', kwargs={'id': coupon1_user.id})
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
            "coupon_amount", "payment_time", "remark", "order_id", "app_id", "app_service_id",
            'payable_amounts', 'creation_time', 'status', 'status_desc'
        ], results[0]["payment_history"])
        self.assertEqual('88.80', results[0]["before_payment"])
        self.assertEqual('-66.66', results[0]["amounts"])
        self.assertEqual('22.14', results[0]["after_payment"])
        self.assertEqual('-66.66', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])

        with self.assertRaises(errors.ConflictError) as cm:
            PaymentManager().pay_by_user(
                user_id=self.user.id, app_id=self.app.id,
                subject='test user pay', amounts=Decimal('66'),
                executor='test',
                remark='test',
                order_id='123',
                app_service_id=self.app_service1.id,
                instance_id='',
                coupon_ids=None,
                only_coupon=False,
                required_enough_balance=False
            )
            self.assertEqual(cm.exception.code, 'OrderIdExist')

        PaymentManager().pay_by_user(
            user_id=self.user.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66'),
            executor='test',
            remark='test',
            order_id='456',
            app_service_id=self.app_service1.id,
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )
        base_url = reverse('wallet-api:cashcoupon-list-payment', kwargs={'id': coupon1_user.id})
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
            order_id='789',
            app_service_id=self.app_service1.id,
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )

        # list vo coupon payment
        base_url = reverse('wallet-api:cashcoupon-list-payment', kwargs={'id': coupon1_vo.id})
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
            "coupon_amount", "payment_time", "remark", "order_id", "app_id", "app_service_id",
            'payable_amounts', 'creation_time', 'status', 'status_desc'
        ], results[0]["payment_history"])
        self.assertEqual('-66.66', results[0]["amounts"])
        self.assertEqual('188.80', results[0]["before_payment"])
        self.assertEqual('122.14', results[0]["after_payment"])
        self.assertEqual('-66.66', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])

        pay_history2 = PaymentManager().pay_by_vo(
            vo_id=self.vo.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66'),
            executor='test',
            remark='test',
            order_id='12356',
            app_service_id=self.app_service1.id,
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )
        base_url = reverse('wallet-api:cashcoupon-list-payment', kwargs={'id': coupon1_vo.id})
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
        self.assertEqual(results[0]["payment_history"]['status'], PaymentHistory.Status.SUCCESS.value)

        # 交易流水
        tbills = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.PAYMENT.value, trade_id=pay_history2.id).all()
        tbill: TransactionBill = tbills[0]
        self.vo.vopointaccount.refresh_from_db()
        self.assertEqual(tbill.account, '')     # 全部代金券支付时为空
        self.assertEqual(tbill.coupon_amount, Decimal('-66'))
        self.assertEqual(tbill.amounts, Decimal('0.00'))
        self.assertEqual(tbill.after_balance, self.vo.vopointaccount.balance)
        self.assertEqual(tbill.owner_type, OwnerType.VO.value)
        self.assertEqual(tbill.owner_id, self.vo.id)
        self.assertEqual(tbill.owner_name, self.vo.name)
        self.assertEqual(tbill.app_service_id, self.app_service1.id)
        self.assertEqual(tbill.app_id, pay_history2.app_id)
        self.assertEqual(tbill.trade_type, TransactionBill.TradeType.PAYMENT.value)
        self.assertEqual(tbill.trade_id, pay_history2.id)

        # 券退款记录测试
        PaymentManager().refund_for_payment(
            app_id=self.app.id, payment_history=pay_history2, out_refund_id='out_refund_id1', refund_reason='test',
            refund_amounts=Decimal('55.66'), remark='test remark', is_refund_coupon=True
        )
        base_url = reverse('wallet-api:cashcoupon-list-payment', kwargs={'id': coupon1_vo.id})
        response = self.client.get(f"{base_url}?{parse.urlencode(query={'page_size': 1})}")
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual('55.66', results[0]["amounts"])
        self.assertEqual('-66.00', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])
        self.assertEqual(results[0]["payment_history"]['status'], PaymentHistory.Status.SUCCESS.value)
        self.assertEqual('66.00', results[0]["refund_history"]['total_amounts'])
        self.assertEqual('55.66', results[0]["refund_history"]['refund_amounts'])
        self.assertEqual('0.00', results[0]["refund_history"]['real_refund'])
        self.assertEqual('55.66', results[0]["refund_history"]['coupon_refund'])
        self.assertEqual(results[0]["refund_history"]['status'], RefundRecord.Status.SUCCESS.value)
        self.assertKeysIn(keys=[
            'id', 'trade_id', 'out_order_id', 'out_refund_id', 'refund_reason', 'total_amounts',
            'refund_amounts', 'real_refund', 'coupon_refund', 'creation_time', 'success_time',
            'status', 'status_desc', 'remark', 'owner_id', 'owner_name', 'owner_type'
        ], container=results[0]["refund_history"])

    def test_exchange_cash_coupon(self):
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

        base_url = reverse('wallet-api:cashcoupon-exchange-coupon')

        # required param "code"
        query = parse.urlencode(query={'id': coupon1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingCode', response=response)

        query = parse.urlencode(query={'code': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidCode', response=response)

        query = parse.urlencode(query={'code': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidCode', response=response)

        # param "vo_id"
        query = parse.urlencode(query={'code': 'testtesteset', 'vo_id': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidVoId', response=response)

        # not cash coupon
        query = parse.urlencode(query={'code': 'testtesteset'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # invalid coupon code
        query = parse.urlencode(query={'code': f'{coupon1.id}#test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='InvalidCouponCode', response=response)

        # no bind app_service, InvalidCoupon
        query = parse.urlencode(query={'code': f'{coupon1.id}#{coupon1.coupon_code}'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='InvalidCoupon', response=response)

        coupon1.app_service_id = self.app_service1.id
        coupon1.save(update_fields=['app_service_id'])

        # ok
        query = parse.urlencode(query={'code': f'{coupon1.id}#{coupon1.coupon_code}'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], coupon1.id)
        coupon1.refresh_from_db()
        self.assertEqual(coupon1.user_id, self.user.id)
        self.assertEqual(coupon1.owner_type, OwnerType.USER.value)
        self.assertEqual(coupon1.vo_id, None)
        self.assertEqual(coupon1.status, CashCoupon.Status.AVAILABLE.value)

        # failed if again
        query = parse.urlencode(query={'code': coupon1.one_exchange_code})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='AlreadyGranted', response=response)

        # not vo
        query = parse.urlencode(query={'code': coupon2.one_exchange_code, 'vo_id': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 404)

        # no vo permission
        query = parse.urlencode(query={'code': coupon2.one_exchange_code, 'vo_id': self.vo.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user=self.user, vo=self.vo, role=VoMember.Role.LEADER.value, inviter='').save(force_insert=True)

        # no bind app_service, InvalidCoupon
        query = parse.urlencode(query={'code': coupon2.one_exchange_code, 'vo_id': self.vo.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='InvalidCoupon', response=response)

        # only coupon that binded app_server is vms-server can to vo
        coupon2.app_service_id = self.app_service2.id
        coupon2.save(update_fields=['app_service_id'])
        query = parse.urlencode(query={'code': coupon2.one_exchange_code, 'vo_id': self.vo.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='NotAllowToVo', response=response)

        # ok
        coupon2.app_service_id = self.app_service1.id
        coupon2.save(update_fields=['app_service_id'])

        query = parse.urlencode(query={'code': coupon2.one_exchange_code, 'vo_id': self.vo.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], coupon2.id)
        coupon2.refresh_from_db()
        self.assertEqual(coupon2.user_id, self.user.id)
        self.assertEqual(coupon2.owner_type, OwnerType.VO.value)
        self.assertEqual(coupon2.vo_id, self.vo.id)
        self.assertEqual(coupon2.status, CashCoupon.Status.AVAILABLE.value)

    def test_detail_cash_coupon(self):
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

        # NotAuthenticated
        self.client.logout()
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': 66})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # user2, NoSuchCoupon
        self.client.force_login(self.user2)
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': 66})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # user2, AccessDenied
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon1_user.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # user2, vo, ok
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon1_vo.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            "id", "face_value", "creation_time", "effective_time", "expiration_time",
            "balance", "status", "granted_time", "issuer", 'use_scope', 'order_id',
            "owner_type", "app_service", "user", "vo", "activity", 'remark'], response.data
        )
        self.assertKeysIn([
            "id", "name", "name_en", "service_id", "category"], response.data['app_service']
        )
        self.assertKeysIn(["id", "name"], response.data['vo'])
        self.assertIsNone(response.data['user'])
        self.assertIsNone(response.data['activity'])

        # user1, NoSuchCoupon
        self.client.logout()
        self.client.force_login(self.user)
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': 66})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # user1, vo, AccessDenied
        self.client.logout()
        self.client.force_login(self.user)
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon1_vo.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # user1, ok
        self.client.logout()
        self.client.force_login(self.user)
        url = reverse('wallet-api:cashcoupon-detail', kwargs={'id': coupon1_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            "id", "face_value", "creation_time", "effective_time", "expiration_time",
            "balance", "status", "granted_time",
            "owner_type", "app_service", "user", "vo", "activity"], response.data
        )
        self.assertKeysIn([
            "id", "name", "name_en", "service_id", "category"], response.data['app_service']
        )
        self.assertKeysIn(["id", "username"], response.data['user'])
        self.assertIsNone(response.data['vo'])
        self.assertIsNone(response.data['activity'])


class AdminCashCouponTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.user2 = get_or_create_user(username='user2')
        self.service = get_or_create_service()

        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        self.app = app
        po = get_or_create_organization(name='机构')
        po.save()
        self.app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service_id=self.service.id,
            category=PayAppService.Category.VMS_SERVER.value
        )
        self.app_service1.save()
        self.app_service2 = PayAppService(
            name='service2', app=app, orgnazition=po, category=PayAppService.Category.VMS_OBJECT.value
        )
        self.app_service2.save()

    def test_admin_create_coupon(self):
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)

        now_time = timezone.now()
        url = reverse('wallet-api:admin-coupon-list')

        # InvalidFaceValue
        data = {
            "face_value": "string",
            "effective_time": "2022-10-21T05:56:35.930Z",
            "expiration_time": "2022-10-21T05:56:35.930Z",
            "app_service_id": "string",
            "username": "string"
        }
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidFaceValue', response=r)
        data['face_value'] = '-10.12'
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidFaceValue', response=r)
        data['face_value'] = '10.123'
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidFaceValue', response=r)

        # InvalidEffectiveTime
        data = {
            "face_value": "66.88",
            "effective_time": "2022-10-21T5:56:",
            "expiration_time": "2022-10-21T05:56:35.930Z",
            "app_service_id": "string",
            "username": "string"
        }
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidEffectiveTime', response=r)

        # InvalidExpirationTime

        now_time_str = to_isoformat(now_time)
        data = {
            "face_value": "66.88",
            "effective_time": now_time_str,
            "expiration_time": "2022-10-21T05:56:35.",
            "app_service_id": "string",
            "username": "string"
        }
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidExpirationTime', response=r)

        # expiration_time < now
        data['expiration_time'] = to_isoformat(now_time - timedelta(minutes=30))
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidExpirationTime', response=r)

        # expiration_time < now
        data['expiration_time'] = to_isoformat(now_time - timedelta(hours=1, minutes=30))
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidExpirationTime', response=r)

        # expiration_time - now < 1 h
        data['expiration_time'] = now_time_str
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidExpirationTime', response=r)

        data['expiration_time'] = to_isoformat(now_time + timedelta(minutes=59))
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidExpirationTime', response=r)

        # expiration_time - now > 1 h
        data['expiration_time'] = to_isoformat(now_time + timedelta(hours=1, minutes=30))
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=404, code='AppServiceNotExist', response=r)

        # expiration_time - effective_time < 1 h
        data['effective_time'] = to_isoformat(now_time + timedelta(minutes=59))
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidExpirationTime', response=r)

        # app_service1 AccessDenied
        data = {
            "face_value": "66.88",
            "effective_time": now_time_str,
            "expiration_time": to_isoformat(now_time + timedelta(hours=1, minutes=30)),
            "app_service_id": self.app_service1.id,
            "username": "string"
        }
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # app_service1 has permission
        self.app_service1.users.add(self.user)
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=404, code='UserNotExist', response=r)

        # app_service2 AccessDenied
        data['app_service_id'] = self.app_service2.id
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # ok, create to user2
        expiration_time_str = to_isoformat(now_time + timedelta(hours=1, minutes=30))
        data = {
            "face_value": "66.88",
            "effective_time": now_time_str,
            "expiration_time": expiration_time_str,
            "app_service_id": self.app_service1.id,
            "username": self.user2.username,
            'remark': 'test remark'
        }
        r = self.client.post(url, data=data)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'face_value', 'creation_time', 'effective_time', 'expiration_time', 'balance', 'status',
            'granted_time', 'owner_type', 'app_service', 'user', 'vo', 'activity', 'exchange_code', "issuer", 'remark'
        ], container=r.data)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'category', 'service_id'
        ], container=r.data['app_service'])
        self.assert_is_subdict_of(sub={
            'face_value': '66.88', 'balance': '66.88', 'owner_type': 'user', 'effective_time': now_time_str,
            'expiration_time': expiration_time_str, 'status': 'available', 'vo': None, 'activity': None,
            'remark': 'test remark'
        }, d=r.data)
        self.assertEqual(r.data['app_service']['id'], self.app_service1.id)
        self.assertEqual(r.data['app_service']['service_id'], self.service.id)
        self.assertEqual(r.data['user']['id'], self.user2.id)
        user2_cps = CashCoupon.objects.filter(user_id=self.user2.id, owner_type=OwnerType.USER.value).all()
        self.assertEqual(len(user2_cps), 1)

        # ok, create no username
        expiration_time_str = to_isoformat(now_time + timedelta(hours=1, minutes=30))
        data = {
            "face_value": "166.88",
            "effective_time": now_time_str,
            "expiration_time": expiration_time_str,
            "app_service_id": self.app_service1.id
        }
        r = self.client.post(url, data=data)
        self.assertEqual(r.status_code, 200)
        self.assert_is_subdict_of(sub={
            'face_value': '166.88', 'balance': '166.88', 'owner_type': '', 'effective_time': now_time_str,
            'expiration_time': expiration_time_str, 'status': 'wait', 'vo': None, 'activity': None
        }, d=r.data)
        self.assertEqual(r.data['app_service']['id'], self.app_service1.id)
        self.assertEqual(r.data['app_service']['service_id'], self.service.id)
        self.assertIsNone(r.data['user'])

        # no permission
        self.app_service1.users.remove(self.user)
        expiration_time_str = to_isoformat(now_time + timedelta(hours=1, minutes=30))
        data = {
            "face_value": "66.88",
            "effective_time": now_time_str,
            "expiration_time": expiration_time_str,
            "app_service_id": self.app_service1.id,
            "username": self.user2.username
        }
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # federal admin
        self.user.set_federal_admin()
        data = {
            "face_value": "66.88",
            "effective_time": now_time_str,
            "expiration_time": expiration_time_str,
            "app_service_id": self.app_service1.id,
            "username": self.user2.username
        }
        r = self.client.post(url, data=data)
        self.assertEqual(r.status_code, 200)

        user2_cps = CashCoupon.objects.filter(user_id=self.user2.id, owner_type=OwnerType.USER.value).all()
        self.assertEqual(len(user2_cps), 2)
        cp_len = CashCoupon.objects.count()
        self.assertEqual(cp_len, 3)

        # 不能同时指定user和vo
        data = {
            "face_value": "66.88",
            "effective_time": now_time_str,
            "expiration_time": expiration_time_str,
            "app_service_id": self.app_service1.id,
            "username": self.user2.username,
            "vo_id": vo1.id
        }
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # VoNotExist
        data = {
            "face_value": "66.88",
            "effective_time": now_time_str,
            "expiration_time": expiration_time_str,
            "app_service_id": self.app_service1.id,
            "vo_id": 'xxxx'
        }
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=404, code='VoNotExist', response=r)

        # VoNotExist
        data = {
            "face_value": "166.88",
            "effective_time": now_time_str,
            "expiration_time": expiration_time_str,
            "app_service_id": self.app_service1.id,
            "vo_id": vo1.id
        }
        r = self.client.post(url, data=data)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'face_value', 'creation_time', 'effective_time', 'expiration_time', 'balance', 'status',
            'granted_time', 'owner_type', 'app_service', 'user', 'vo', 'activity', 'exchange_code', "issuer"
        ], container=r.data)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'category', 'service_id'
        ], container=r.data['app_service'])
        self.assert_is_subdict_of(sub={
            'face_value': '166.88', 'balance': '166.88', 'owner_type': 'vo', 'effective_time': now_time_str,
            'expiration_time': expiration_time_str, 'status': 'available', 'activity': None
        }, d=r.data)
        self.assertEqual(r.data['app_service']['id'], self.app_service1.id)
        self.assertEqual(r.data['app_service']['service_id'], self.service.id)
        self.assertEqual(r.data['user']['id'], self.user.id)
        self.assertEqual(r.data['vo']['id'], vo1.id)
        vo1_cps = CashCoupon.objects.filter(vo_id=vo1.id, owner_type=OwnerType.VO.value).all()
        self.assertEqual(len(vo1_cps), 1)
        cp_len = CashCoupon.objects.count()
        self.assertEqual(cp_len, 4)

    def test_admin_list_coupon(self):
        template = CashCouponActivity(
            name='test template', app_service_id=self.app_service1.id,
            face_value=Decimal('66'), effective_time=timezone.now(), expiration_time=timezone.now() + timedelta(days=1)
        )
        template.save(force_insert=True)
        wait_coupon1, coupon_num = CashCouponActivityManager.clone_coupon(
            activity=template, coupon_num=0, issuer=self.user2.username)

        coupon2 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=timezone.now() - timedelta(days=1),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.AVAILABLE.value,
            app_service_id=self.app_service1.id,
            user_id=self.user.id,
            owner_type=OwnerType.USER.value,
            issuer='test@cnic.cn'
        )
        coupon2.save(force_insert=True)

        coupon3 = CashCoupon(
            face_value=Decimal('66.68'),
            balance=Decimal('66.68'),
            effective_time=timezone.now() + timedelta(days=1),
            expiration_time=timezone.now() + timedelta(days=2),
            status=CashCoupon.Status.AVAILABLE.value,
            app_service_id=self.app_service2.id,
            user_id=self.user2.id,
            owner_type=OwnerType.USER.value,
            issuer='test@cnic.cn'
        )
        coupon3.save(force_insert=True)

        # user no permission of app_service1
        url = reverse('wallet-api:admin-coupon-list')
        query = parse.urlencode(query={'app_service_id': self.app_service1.id})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        url = reverse('wallet-api:admin-coupon-list')
        query = parse.urlencode(query={'template_id': template.id})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # no query
        query = parse.urlencode(query={})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # user has permission of app_service1
        self.app_service1.users.add(self.user)

        # no query
        query = parse.urlencode(query={})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['app_service']['id'], self.app_service1.id)
        self.assertEqual(r.data['results'][0]['id'], coupon2.id)
        self.assertEqual(r.data['results'][1]['app_service']['id'], self.app_service1.id)
        self.assertEqual(r.data['results'][1]['id'], wait_coupon1.id)

        # query "id"
        query = parse.urlencode(query={'id': coupon2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], coupon2.id)

        query = parse.urlencode(query={'id': 'coupon2.id'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # query "page_size"
        query = parse.urlencode(query={'app_service_id': self.app_service1.id, 'page_size': 1})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], coupon2.id)

        # query "app_service_id"
        query = parse.urlencode(query={'app_service_id': self.app_service1.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'id', 'face_value', 'creation_time', 'effective_time', 'expiration_time', 'balance', 'status',
            'granted_time', 'owner_type', 'app_service', 'user', 'vo', 'activity', 'exchange_code', "issuer", 'remark',
            'use_scope', 'order_id'
        ], container=r.data['results'][0])

        # user has permission of app_service1, query "app_service_id", "status"
        query = parse.urlencode(query={
            'app_service_id': self.app_service1.id, 'status': CashCoupon.Status.AVAILABLE.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], coupon2.id)

        # user no permission of app_service1, query "template_id"
        self.app_service1.users.remove(self.user)
        query = parse.urlencode(query={'template_id': template.id})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user has permission of app_service1, query "template_id"
        self.app_service1.users.add(self.user)
        query = parse.urlencode(query={'template_id': template.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertKeysIn(keys=[
            'id', 'face_value', 'creation_time', 'effective_time', 'expiration_time', 'balance', 'status',
            'granted_time', 'owner_type', 'app_service', 'user', 'vo', 'activity', 'exchange_code',
            'use_scope', 'order_id'
        ], container=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['id'], wait_coupon1.id)

        # user has permission of app_service1, query "template_id", "download"
        query = parse.urlencode(query={'template_id': template.id, 'download': ''})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.streaming, True)

        # no permission
        self.app_service1.users.remove(self.user)
        query = parse.urlencode(query={})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # federal admin
        self.user.set_federal_admin()

        query = parse.urlencode(query={})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(len(r.data['results']), 3)

        # query "id"
        query = parse.urlencode(query={'id': coupon2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], coupon2.id)

        query = parse.urlencode(query={'id': 'coupon2.id'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # query "valid_status"
        query = parse.urlencode(query={'valid_status': QueryCouponValidChoices.NOT_YET.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], coupon3.id)

        query = parse.urlencode(query={'valid_status': QueryCouponValidChoices.VALID.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], wait_coupon1.id)

        query = parse.urlencode(query={'valid_status': QueryCouponValidChoices.EXPIRED.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], coupon2.id)

        # query "issuer"、 "redeemer"
        query = parse.urlencode(query={'issuer': ''})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'redeemer': ''})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'redeemer': 'notfount'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='UserNotExist', response=r)

        query = parse.urlencode(query={'issuer': 'test@cnic.cn'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], coupon3.id)
        self.assertEqual(r.data['results'][1]['id'], coupon2.id)

        query = parse.urlencode(query={'issuer': 'fff'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'issuer': self.user2.username})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], wait_coupon1.id)

        query = parse.urlencode(query={'redeemer': self.user.username})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], coupon2.id)

        query = parse.urlencode(query={'redeemer': self.user2.username})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], coupon3.id)

        # query "time_start"
        url = reverse('wallet-api:admin-coupon-list')
        query = parse.urlencode(query={'time_start': '2023-04-01T08:08:01'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        nt = timezone.now()
        tstart = (nt - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        query = parse.urlencode(query={'time_start': tstart})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(len(r.data['results']), 3)

        tstart = (nt + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        query = parse.urlencode(query={'time_start': tstart})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # query "time_end"
        url = reverse('wallet-api:admin-coupon-list')
        query = parse.urlencode(query={'time_end': '2023-04-01T08:08:01'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        nt = timezone.now()
        tend = (nt - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        query = parse.urlencode(query={'time_end': tend})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        tend = (nt + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        query = parse.urlencode(query={'time_end': tend})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(len(r.data['results']), 3)

        # query "time_start", "time_end"
        url = reverse('wallet-api:admin-coupon-list')
        nt = timezone.now()
        tstart = (nt - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        tend = (nt + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        query = parse.urlencode(query={'time_start': tend, 'time_end': tstart})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'time_start': tstart, 'time_end': tend})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(len(r.data['results']), 3)

        # owner_type, vo_id
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)
        vo_coupon4 = CashCoupon(
            face_value=Decimal('466.68'),
            balance=Decimal('466.68'),
            effective_time=timezone.now() + timedelta(days=1),
            expiration_time=timezone.now() + timedelta(days=6),
            status=CashCoupon.Status.AVAILABLE.value,
            app_service_id=self.app_service2.id,
            user_id=self.user2.id,
            owner_type=OwnerType.VO.value,
            vo=vo1,
            issuer='test@cnic.cn'
        )
        vo_coupon4.save(force_insert=True)

        query = parse.urlencode(query={'owner_type': 'user'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)

        query = parse.urlencode(query={'owner_type': 'vo'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], vo_coupon4.id)

        query = parse.urlencode(query={'vo_id': vo1.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], vo_coupon4.id)

        query = parse.urlencode(query={'vo_id': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

    def test_delete_cash_coupon(self):
        coupon2 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=timezone.now(),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.WAIT.value,
            app_service_id=self.app_service1.id,
            user_id=self.user.id
        )
        coupon2.save(force_insert=True)

        coupon3 = CashCoupon(
            face_value=Decimal('66.68'),
            balance=Decimal('66.68'),
            effective_time=timezone.now(),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.AVAILABLE.value,
            app_service_id=self.app_service2.id,
            user_id=self.user2.id
        )
        coupon3.save(force_insert=True)

        # NotAuthenticated
        self.client.logout()
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': 'notfound'})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # NoSuchCoupon
        self.client.force_login(self.user)
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': 'notfound'})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # AccessDenied
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': coupon2.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # delete coupon2 ok, app_service1 admin
        coupon2.app_service.users.add(self.user)
        self.assertEqual(coupon2.status, CashCoupon.Status.WAIT.value)
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': coupon2.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        coupon2.refresh_from_db()
        self.assertEqual(coupon2.status, CashCoupon.Status.DELETED.value)

        # delete coupon3, AccessDenied
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': coupon3.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # delete coupon3 ok, federal admin
        self.user.set_federal_admin()
        self.assertEqual(coupon3.status, CashCoupon.Status.AVAILABLE.value)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        coupon3.refresh_from_db()
        self.assertEqual(coupon3.status, CashCoupon.Status.DELETED.value)

    def test_detail_cash_coupon(self):
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)

        coupon2 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=timezone.now(),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.WAIT.value,
            app_service_id=self.app_service1.id,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id
        )
        coupon2.save(force_insert=True)

        coupon3 = CashCoupon(
            face_value=Decimal('166.68'),
            balance=Decimal('66.68'),
            effective_time=timezone.now(),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.AVAILABLE.value,
            app_service_id=self.app_service2.id,
            owner_type=OwnerType.VO.value,
            user_id=self.user2.id,
            vo_id=vo1.id
        )
        coupon3.save(force_insert=True)

        # NotAuthenticated
        self.client.logout()
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': 'notfound'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # NoSuchCoupon
        self.client.force_login(self.user)
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': 'notfound'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # AccessDenied
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': coupon2.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # get coupon2 ok, app_service1 admin
        coupon2.app_service.users.add(self.user)
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': coupon2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'face_value', 'creation_time', 'effective_time', 'expiration_time', 'balance', 'status',
            'granted_time', 'owner_type', 'app_service', 'user', 'vo', 'activity', 'exchange_code', "issuer", 'remark',
            'use_scope', 'order_id'
        ], container=response.data)
        self.assertKeysIn(keys=['id', 'name', 'service_id'], container=response.data['app_service'])
        self.assertKeysIn(keys=['id', 'username'], container=response.data['user'])
        self.assertEqual(response.data['id'], coupon2.id)
        self.assertEqual(response.data['face_value'], '66.60')

        # get coupon3, AccessDenied
        url = reverse('wallet-api:admin-coupon-detail', kwargs={'id': coupon3.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # get coupon3 ok, federal admin
        self.user.set_federal_admin()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'face_value', 'creation_time', 'effective_time', 'expiration_time', 'balance', 'status',
            'granted_time', 'owner_type', 'app_service', 'user', 'vo', 'activity', 'exchange_code',
            'use_scope', 'order_id'
        ], container=response.data)
        self.assertKeysIn(keys=['id', 'name', 'service_id'], container=response.data['app_service'])
        self.assertKeysIn(keys=['id', 'username'], container=response.data['user'])
        self.assertKeysIn(keys=['id', 'name'], container=response.data['vo'])
        self.assertEqual(response.data['id'], coupon3.id)
        self.assertEqual(response.data['face_value'], '166.68')

    def test_admin_list_coupon_payments(self):
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)

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
            vo=vo1,
            app_service_id=self.app_service2.id
        )
        coupon1_vo.save(force_insert=True)

        # NotAuthenticated
        self.client.logout()
        url = reverse('wallet-api:admin-coupon-list-payment', kwargs={'id': 'notfound'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # NoSuchCoupon
        self.client.force_login(self.user)
        url = reverse('wallet-api:admin-coupon-list-payment', kwargs={'id': 'notfound'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # AccessDenied
        url = reverse('wallet-api:admin-coupon-list-payment', kwargs={'id': coupon1_user.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # ------- list user coupon payment historys -------
        coupon1_user.app_service.users.add(self.user)
        # list user coupon payment
        base_url = reverse('wallet-api:admin-coupon-list-payment', kwargs={'id': coupon1_user.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        PaymentManager().pay_by_user(
            user_id=self.user.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66.66'),
            executor='test',
            remark='test',
            order_id='123',
            app_service_id=self.app_service1.id,
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )

        # list user coupon payment
        base_url = reverse('wallet-api:admin-coupon-list-payment', kwargs={'id': coupon1_user.id})
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
            "coupon_amount", "payment_time", "remark", "order_id", "app_id", "app_service_id",
            'payable_amounts', 'creation_time', 'status', 'status_desc'
        ], results[0]["payment_history"])
        self.assertEqual('88.80', results[0]["before_payment"])
        self.assertEqual('-66.66', results[0]["amounts"])
        self.assertEqual('22.14', results[0]["after_payment"])
        self.assertEqual('-66.66', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])

        with self.assertRaises(errors.ConflictError) as cm:
            PaymentManager().pay_by_user(
                user_id=self.user.id, app_id=self.app.id,
                subject='test user pay', amounts=Decimal('66'),
                executor='test',
                remark='test',
                order_id='123',
                app_service_id=self.app_service1.id,
                instance_id='',
                coupon_ids=None,
                only_coupon=False,
                required_enough_balance=False
            )
            self.assertEqual(cm.exception.code, 'OrderIdExist')

        PaymentManager().pay_by_user(
            user_id=self.user.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66'),
            executor='test',
            remark='test',
            order_id='456',
            app_service_id=self.app_service1.id,
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )
        base_url = reverse('wallet-api:admin-coupon-list-payment', kwargs={'id': coupon1_user.id})
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
            vo_id=vo1.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66.66'),
            executor='test',
            remark='test',
            order_id='789',
            app_service_id=self.app_service2.id,
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )

        # list vo coupon payment
        base_url = reverse('wallet-api:admin-coupon-list-payment', kwargs={'id': coupon1_vo.id})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
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
            "coupon_amount", "payment_time", "remark", "order_id", "app_id", "app_service_id",
            'payable_amounts', 'creation_time', 'status', 'status_desc'
        ], results[0]["payment_history"])
        self.assertEqual('-66.66', results[0]["amounts"])
        self.assertEqual('188.80', results[0]["before_payment"])
        self.assertEqual('122.14', results[0]["after_payment"])
        self.assertEqual('-66.66', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])

        pay_history2 = PaymentManager().pay_by_vo(
            vo_id=vo1.id, app_id=self.app.id,
            subject='test user pay', amounts=Decimal('66'),
            executor='test',
            remark='test',
            order_id='12356',
            app_service_id=self.app_service2.id,
            instance_id='',
            coupon_ids=None,
            only_coupon=False,
            required_enough_balance=False
        )
        base_url = reverse('wallet-api:admin-coupon-list-payment', kwargs={'id': coupon1_vo.id})
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
        self.assertEqual(results[0]["payment_history"]['status'], PaymentHistory.Status.SUCCESS.value)

        # 交易流水
        tbills = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.PAYMENT.value, trade_id=pay_history2.id).all()
        tbill: TransactionBill = tbills[0]
        vo1.vopointaccount.refresh_from_db()
        self.assertEqual(tbill.account, '')     # 全部代金券支付时为空
        self.assertEqual(tbill.coupon_amount, Decimal('-66'))
        self.assertEqual(tbill.amounts, Decimal('0.00'))
        self.assertEqual(tbill.after_balance, vo1.vopointaccount.balance)
        self.assertEqual(tbill.owner_type, OwnerType.VO.value)
        self.assertEqual(tbill.owner_id, vo1.id)
        self.assertEqual(tbill.owner_name, vo1.name)
        self.assertEqual(tbill.app_service_id, self.app_service2.id)
        self.assertEqual(tbill.app_id, pay_history2.app_id)
        self.assertEqual(tbill.trade_type, TransactionBill.TradeType.PAYMENT.value)
        self.assertEqual(tbill.trade_id, pay_history2.id)

        # 券退款记录测试
        PaymentManager().refund_for_payment(
            app_id=self.app.id, payment_history=pay_history2, out_refund_id='out_refund_id1', refund_reason='test',
            refund_amounts=Decimal('55.66'), remark='test remark', is_refund_coupon=True
        )
        base_url = reverse('wallet-api:cashcoupon-list-payment', kwargs={'id': coupon1_vo.id})
        response = self.client.get(f"{base_url}?{parse.urlencode(query={'page_size': 1})}")
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual('55.66', results[0]["amounts"])
        self.assertEqual('-66.00', results[0]["payment_history"]['coupon_amount'])
        self.assertEqual('0.00', results[0]["payment_history"]['amounts'])
        self.assertEqual(results[0]["payment_history"]['status'], PaymentHistory.Status.SUCCESS.value)
        self.assertEqual('66.00', results[0]["refund_history"]['total_amounts'])
        self.assertEqual('55.66', results[0]["refund_history"]['refund_amounts'])
        self.assertEqual('0.00', results[0]["refund_history"]['real_refund'])
        self.assertEqual('55.66', results[0]["refund_history"]['coupon_refund'])
        self.assertEqual(results[0]["refund_history"]['status'], RefundRecord.Status.SUCCESS.value)
        self.assertKeysIn(keys=[
            'id', 'trade_id', 'out_order_id', 'out_refund_id', 'refund_reason', 'total_amounts',
            'refund_amounts', 'real_refund', 'coupon_refund', 'creation_time', 'success_time',
            'status', 'status_desc', 'remark', 'owner_id', 'owner_name', 'owner_type'
        ], container=results[0]["refund_history"])

    def test_admin_statistics(self):
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)

        now_time = timezone.now()
        coupon1_user = CashCoupon(
            face_value=Decimal('1.11'),
            balance=Decimal('1.11'),
            effective_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            expiration_time=now_time + timedelta(days=2),
            status=CashCoupon.Status.WAIT.value,
            granted_time=None,
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id
        )
        coupon1_user.save(force_insert=True)
        coupon1_user.creation_time = datetime(year=2023, month=4, day=1, tzinfo=utc)
        coupon1_user.save(update_fields=['creation_time'])

        coupon2_user = CashCoupon(
            face_value=Decimal('2.22'),
            balance=Decimal('1.22'),
            effective_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            expiration_time=datetime(year=2023, month=5, day=30, tzinfo=utc),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id
        )
        coupon2_user.save(force_insert=True)
        coupon2_user.creation_time = datetime(year=2023, month=5, day=1, tzinfo=utc)
        coupon2_user.save(update_fields=['creation_time'])

        coupon1_vo = CashCoupon(
            face_value=Decimal('3.33'),
            balance=Decimal('3.33'),
            effective_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            expiration_time=now_time + timedelta(days=1),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            owner_type=OwnerType.VO.value,
            vo=vo1,
            app_service_id=self.app_service1.id
        )
        coupon1_vo.save(force_insert=True)
        coupon1_vo.creation_time = datetime(year=2023, month=5, day=8, tzinfo=utc)
        coupon1_vo.save(update_fields=['creation_time'])

        coupon2_vo = CashCoupon(
            face_value=Decimal('4.44'),
            balance=Decimal('3.3'),
            effective_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            expiration_time=datetime(year=2023, month=6, day=1, tzinfo=utc),
            status=CashCoupon.Status.DELETED.value,
            granted_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            owner_type=OwnerType.VO.value,
            vo=vo1,
            app_service_id=self.app_service2.id
        )
        coupon2_vo.save(force_insert=True)
        coupon2_vo.creation_time = datetime(year=2023, month=5, day=31, tzinfo=utc)
        coupon2_vo.save(update_fields=['creation_time'])

        coupon2_user_pay = CashCouponPaymentHistory(
            payment_history_id=None, cash_coupon_id=coupon2_user.id, amounts=Decimal('-1.01'),
            before_payment=Decimal('0'), after_payment=Decimal('0')
        )
        coupon2_user_pay.save(force_insert=True)
        coupon2_user_pay.creation_time = datetime(year=2023, month=5, day=31, tzinfo=utc)
        coupon2_user_pay.save(update_fields=['creation_time'])

        coupon2_vo_pay = CashCouponPaymentHistory(
            payment_history_id=None, cash_coupon_id=coupon2_vo.id, amounts=Decimal('-0.66'),
            before_payment=Decimal('0'), after_payment=Decimal('0')
        )
        coupon2_vo_pay.save(force_insert=True)

        # NotAuthenticated
        self.client.logout()
        base_url = reverse('wallet-api:admin-coupon-statistics')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # AccessDenied
        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00', 'time_end': '2023-05-10T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'total_face_value', 'total_count', 'redeem_count', 'available_count', 'coupon_pay_amounts', 'total_balance'
        ], container=response.data)
        self.assertEqual(Decimal(response.data['total_face_value']), Decimal(f'{(1.11+2.22+3.33+4.44):.2f}'))
        self.assertEqual(response.data['total_count'], 4)
        self.assertEqual(response.data['redeem_count'], 3)
        self.assertEqual(response.data['available_count'], 1)
        self.assertEqual(Decimal(response.data['coupon_pay_amounts']), Decimal(f'{(1.01+0.66):.2f}'))
        self.assertEqual(Decimal(response.data['total_balance']), Decimal('3.33'))      # 当前有效券余额

        # app_service_id
        query = parse.urlencode(query={'app_service_id': self.app_service1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data['total_face_value']), Decimal(f'{(1.11 + 2.22 + 3.33):.2f}'))
        self.assertEqual(response.data['total_count'], 3)
        self.assertEqual(response.data['redeem_count'], 2)
        self.assertEqual(response.data['available_count'], 1)
        self.assertEqual(Decimal(response.data['coupon_pay_amounts']), Decimal('1.01'))
        self.assertEqual(Decimal(response.data['total_balance']), Decimal('3.33'))

        query = parse.urlencode(query={'app_service_id': self.app_service2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data['total_face_value']), Decimal(f'{4.44:.2f}'))
        self.assertEqual(response.data['total_count'], 1)
        self.assertEqual(response.data['redeem_count'], 1)
        self.assertEqual(response.data['available_count'], 0)
        self.assertEqual(Decimal(response.data['coupon_pay_amounts']), Decimal('0.66'))
        self.assertEqual(Decimal(response.data['total_balance']), Decimal('0.00'))

        # time_start, time_end
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00Z', 'time_end': '2023-05-10T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data['total_face_value']), Decimal(f'{(2.22 + 3.33):.2f}'))
        self.assertEqual(response.data['total_count'], 2)
        self.assertEqual(response.data['redeem_count'], 2)
        self.assertEqual(response.data['available_count'], 1)
        self.assertEqual(Decimal(response.data['coupon_pay_amounts']), Decimal('0.00'))
        self.assertEqual(Decimal(response.data['total_balance']), Decimal('3.33'))

        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00Z', 'time_end': '2023-06-01T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data['total_face_value']), Decimal(f'{(2.22 + 3.33 + 4.44):.2f}'))
        self.assertEqual(response.data['total_count'], 3)
        self.assertEqual(response.data['redeem_count'], 3)
        self.assertEqual(response.data['available_count'], 1)
        self.assertEqual(Decimal(response.data['coupon_pay_amounts']), Decimal(f'{1.01:.2f}'))
        self.assertEqual(Decimal(response.data['total_balance']), Decimal('3.33'))

        # time_start, time_end, app_service_id
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00Z', 'time_end': '2023-06-01T00:00:00Z',
            'app_service_id': self.app_service2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data['total_face_value']), Decimal(f'{4.44:.2f}'))
        self.assertEqual(response.data['total_count'], 1)
        self.assertEqual(response.data['redeem_count'], 1)
        self.assertEqual(response.data['available_count'], 0)
        self.assertEqual(Decimal(response.data['coupon_pay_amounts']), Decimal('0.00'))
        self.assertEqual(Decimal(response.data['total_balance']), Decimal('0'))

    def test_admin_issue_statistics(self):
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)

        now_time = timezone.now()
        coupon1_user = CashCoupon(
            face_value=Decimal('1.11'),
            balance=Decimal('1.11'),
            effective_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            expiration_time=now_time + timedelta(days=2),
            status=CashCoupon.Status.WAIT.value,
            granted_time=None,
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id,
            issuer='user1'
        )
        coupon1_user.save(force_insert=True)
        coupon1_user.creation_time = datetime(year=2023, month=4, day=1, tzinfo=utc)
        coupon1_user.save(update_fields=['creation_time'])

        coupon2_user = CashCoupon(
            face_value=Decimal('2.22'),
            balance=Decimal('1.22'),
            effective_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            expiration_time=datetime(year=2023, month=5, day=30, tzinfo=utc),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id,
            issuer='user2'
        )
        coupon2_user.save(force_insert=True)
        coupon2_user.creation_time = datetime(year=2023, month=5, day=1, tzinfo=utc)
        coupon2_user.save(update_fields=['creation_time'])

        coupon1_vo = CashCoupon(
            face_value=Decimal('3.33'),
            balance=Decimal('3.33'),
            effective_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            expiration_time=now_time + timedelta(days=1),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            owner_type=OwnerType.VO.value,
            vo=vo1,
            app_service_id=self.app_service1.id,
            issuer=''
        )
        coupon1_vo.save(force_insert=True)
        coupon1_vo.creation_time = datetime(year=2023, month=5, day=8, tzinfo=utc)
        coupon1_vo.save(update_fields=['creation_time'])

        coupon2_vo = CashCoupon(
            face_value=Decimal('4.44'),
            balance=Decimal('3.3'),
            effective_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            expiration_time=datetime(year=2023, month=6, day=1, tzinfo=utc),
            status=CashCoupon.Status.DELETED.value,
            granted_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            owner_type=OwnerType.VO.value,
            vo=vo1,
            app_service_id=self.app_service2.id,
            issuer='user1'
        )
        coupon2_vo.save(force_insert=True)
        coupon2_vo.creation_time = datetime(year=2023, month=5, day=31, tzinfo=utc)
        coupon2_vo.save(update_fields=['creation_time'])

        # NotAuthenticated
        self.client.logout()
        base_url = reverse('wallet-api:admin-coupon-aggregation-issue')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # AccessDenied
        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00', 'time_end': '2023-05-10T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'count', 'page_num', 'page_size', 'results'], container=response.data)
        self.assertKeysIn(keys=[
            'total_face_value', 'total_count', 'issuer'], container=response.data['results'][0])
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 3)

        for item in response.data['results']:
            if item['issuer'] == '':
                self.assertEqual(Decimal(item['total_face_value']), Decimal('3.33'))
                self.assertEqual(item['total_count'], 1)
            elif item['issuer'] == 'user1':
                self.assertEqual(Decimal(item['total_face_value']), Decimal(f'{(1.11 + 4.44):.2f}'))
                self.assertEqual(item['total_count'], 2)
            else:
                self.assertEqual(Decimal(item['total_face_value']), Decimal(f'2.22'))
                self.assertEqual(item['total_count'], 1)
                self.assertEqual(item['issuer'], 'user2')

        # page_size
        query = parse.urlencode(query={'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'count', 'page_num', 'page_size', 'results'], container=response.data)
        self.assertKeysIn(keys=[
            'total_face_value', 'total_count', 'issuer'], container=response.data['results'][0])
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # time_start, time_end
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00Z', 'time_end': '2023-05-10T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)

        item1 = response.data['results'][0]
        item2 = response.data['results'][1]
        if item1['issuer'] == 'user2':
            items = [item1, item2]
        else:
            items = [item2, item1]

        self.assertEqual(items[0]['issuer'], 'user2')
        self.assertEqual(Decimal(items[0]['total_face_value']), Decimal('2.22'))
        self.assertEqual(items[0]['total_count'], 1)
        self.assertEqual(items[1]['issuer'], '')
        self.assertEqual(Decimal(items[1]['total_face_value']), Decimal('3.33'))
        self.assertEqual(items[1]['total_count'], 1)

        # issuer
        query = parse.urlencode(query={'issuer': 'user1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 1)

        item = response.data['results'][0]
        self.assertEqual(Decimal(item['total_face_value']), Decimal(f'{(1.11 + 4.44):.2f}'))
        self.assertEqual(item['total_count'], 2)
        self.assertEqual(item['issuer'], 'user1')

    def test_admin_user_statistics(self):
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)

        now_time = timezone.now()
        coupon1_user = CashCoupon(
            face_value=Decimal('1.11'),
            balance=Decimal('1.11'),
            effective_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            expiration_time=now_time + timedelta(days=2),
            status=CashCoupon.Status.DELETED.value,
            granted_time=None,
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id,
            issuer='user1'
        )
        coupon1_user.save(force_insert=True)
        coupon1_user.creation_time = datetime(year=2023, month=4, day=1, tzinfo=utc)
        coupon1_user.save(update_fields=['creation_time'])

        coupon2_user = CashCoupon(
            face_value=Decimal('2.22'),
            balance=Decimal('1.22'),
            effective_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            expiration_time=datetime(year=2023, month=5, day=30, tzinfo=utc),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id,
            issuer='user2'
        )
        coupon2_user.save(force_insert=True)
        coupon2_user.creation_time = datetime(year=2023, month=5, day=1, tzinfo=utc)
        coupon2_user.save(update_fields=['creation_time'])

        coupon3_user2 = CashCoupon(
            face_value=Decimal('3.33'),
            balance=Decimal('2.33'),
            effective_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            expiration_time=now_time + timedelta(days=1),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            owner_type=OwnerType.USER.value,
            user=self.user2,
            app_service_id=self.app_service1.id,
            issuer=''
        )
        coupon3_user2.save(force_insert=True)
        coupon3_user2.creation_time = datetime(year=2023, month=5, day=8, tzinfo=utc)
        coupon3_user2.save(update_fields=['creation_time'])

        coupon2_vo = CashCoupon(
            face_value=Decimal('4.44'),
            balance=Decimal('3.3'),
            effective_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            expiration_time=datetime(year=2023, month=6, day=1, tzinfo=utc),
            status=CashCoupon.Status.DELETED.value,
            granted_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            owner_type=OwnerType.VO.value,
            vo=vo1,
            app_service_id=self.app_service2.id,
            issuer='user1'
        )
        coupon2_vo.save(force_insert=True)
        coupon2_vo.creation_time = datetime(year=2023, month=5, day=31, tzinfo=utc)
        coupon2_vo.save(update_fields=['creation_time'])

        # NotAuthenticated
        self.client.logout()
        base_url = reverse('wallet-api:admin-coupon-aggregation-user')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # AccessDenied
        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00', 'time_end': '2023-05-10T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'count', 'page_num', 'page_size', 'results'], container=response.data)
        self.assertKeysIn(keys=[
            'user_id', 'username', 'total_face_value', 'total_balance', 'total_count', 'total_valid_count'
        ], container=response.data['results'][0])
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)

        # username
        query = parse.urlencode(query={'username': self.user.username})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 1)

        item = response.data['results'][0]
        self.assertEqual(item['user_id'], self.user.id)
        self.assertEqual(item['username'], self.user.username)
        self.assertEqual(Decimal(item['total_face_value']), Decimal(f'{(1.11 + 2.22):.2f}'))
        self.assertEqual(Decimal(item['total_balance']), Decimal(f'{(1.11 + 1.22):.2f}'))
        self.assertEqual(item['total_count'], 2)
        self.assertEqual(item['total_valid_count'], 0)

        # page_size
        query = parse.urlencode(query={'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # time_start, time_end
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00Z', 'time_end': '2023-05-10T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)

        item1 = response.data['results'][0]
        item2 = response.data['results'][1]
        if item1['username'] == self.user.username:
            items = [item1, item2]
        else:
            items = [item2, item1]

        self.assertEqual(items[0]['user_id'], self.user.id)
        self.assertEqual(items[0]['username'], self.user.username)
        self.assertEqual(Decimal(items[0]['total_face_value']), Decimal('2.22'))
        self.assertEqual(Decimal(items[0]['total_balance']), Decimal('1.22'))
        self.assertEqual(items[0]['total_count'], 1)
        self.assertEqual(items[0]['total_valid_count'], 0)

        self.assertEqual(items[1]['user_id'], self.user2.id)
        self.assertEqual(items[1]['username'], self.user2.username)
        self.assertEqual(Decimal(items[1]['total_face_value']), Decimal('3.33'))
        self.assertEqual(Decimal(items[1]['total_balance']), Decimal('2.33'))
        self.assertEqual(items[1]['total_count'], 1)
        self.assertEqual(items[1]['total_valid_count'], 1)

    def test_admin_vo_statistics(self):
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)

        now_time = timezone.now()
        coupon1_user = CashCoupon(
            face_value=Decimal('1.11'),
            balance=Decimal('1.11'),
            effective_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            expiration_time=now_time + timedelta(days=2),
            status=CashCoupon.Status.DELETED.value,
            granted_time=None,
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id,
            issuer='user1'
        )
        coupon1_user.save(force_insert=True)
        coupon1_user.creation_time = datetime(year=2023, month=4, day=1, tzinfo=utc)
        coupon1_user.save(update_fields=['creation_time'])

        coupon2_user = CashCoupon(
            face_value=Decimal('2.22'),
            balance=Decimal('1.22'),
            effective_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            expiration_time=datetime(year=2023, month=5, day=30, tzinfo=utc),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            owner_type=OwnerType.USER.value,
            user=self.user,
            app_service_id=self.app_service1.id,
            issuer='user2'
        )
        coupon2_user.save(force_insert=True)
        coupon2_user.creation_time = datetime(year=2023, month=5, day=1, tzinfo=utc)
        coupon2_user.save(update_fields=['creation_time'])

        coupon3_vo = CashCoupon(
            face_value=Decimal('3.33'),
            balance=Decimal('2.33'),
            effective_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            expiration_time=now_time + timedelta(days=1),
            status=CashCoupon.Status.AVAILABLE.value,
            granted_time=datetime(year=2023, month=5, day=1, tzinfo=utc),
            owner_type=OwnerType.VO.value,
            vo=vo1,
            app_service_id=self.app_service1.id,
            issuer=''
        )
        coupon3_vo.save(force_insert=True)
        coupon3_vo.creation_time = datetime(year=2023, month=5, day=8, tzinfo=utc)
        coupon3_vo.save(update_fields=['creation_time'])

        coupon2_vo = CashCoupon(
            face_value=Decimal('4.44'),
            balance=Decimal('3.3'),
            effective_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            expiration_time=datetime(year=2023, month=6, day=1, tzinfo=utc),
            status=CashCoupon.Status.DELETED.value,
            granted_time=datetime(year=2023, month=5, day=10, tzinfo=utc),
            owner_type=OwnerType.VO.value,
            vo=vo1,
            app_service_id=self.app_service2.id,
            issuer='user1'
        )
        coupon2_vo.save(force_insert=True)
        coupon2_vo.creation_time = datetime(year=2023, month=5, day=31, tzinfo=utc)
        coupon2_vo.save(update_fields=['creation_time'])

        # NotAuthenticated
        self.client.logout()
        base_url = reverse('wallet-api:admin-coupon-aggregation-vo')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # AccessDenied
        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00', 'time_end': '2023-05-10T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'count', 'page_num', 'page_size', 'results'], container=response.data)
        self.assertKeysIn(keys=[
            'vo_id', 'name', 'total_face_value', 'total_balance', 'total_count', 'total_valid_count'
        ], container=response.data['results'][0])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 1)

        # username
        query = parse.urlencode(query={'voname': vo1.name})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 1)

        item = response.data['results'][0]
        self.assertEqual(item['vo_id'], vo1.id)
        self.assertEqual(item['name'], vo1.name)
        self.assertEqual(Decimal(item['total_face_value']), Decimal(f'{(3.33 + 4.44):.2f}'))
        self.assertEqual(Decimal(item['total_balance']), Decimal(f'{(2.33 + 3.3):.2f}'))
        self.assertEqual(item['total_count'], 2)
        self.assertEqual(item['total_valid_count'], 1)

        # page_size
        query = parse.urlencode(query={'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # time_start, time_end
        query = parse.urlencode(query={
            'time_start': '2023-05-01T00:00:00Z', 'time_end': '2023-05-10T00:00:00Z'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 1)

        item1 = response.data['results'][0]
        self.assertEqual(item1['vo_id'], vo1.id)
        self.assertEqual(item1['name'], vo1.name)
        self.assertEqual(Decimal(item1['total_face_value']), Decimal('3.33'))
        self.assertEqual(Decimal(item1['total_balance']), Decimal('2.33'))
        self.assertEqual(item1['total_count'], 1)
        self.assertEqual(item1['total_valid_count'], 1)

    def test_remark_coupon(self):
        vo1 = VirtualOrganization(name='test vo', owner_id=self.user.id)
        vo1.save(force_insert=True)

        coupon2 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=timezone.now(),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.WAIT.value,
            app_service_id=self.app_service1.id,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id
        )
        coupon2.save(force_insert=True)

        coupon3 = CashCoupon(
            face_value=Decimal('166.68'),
            balance=Decimal('66.68'),
            effective_time=timezone.now(),
            expiration_time=timezone.now(),
            status=CashCoupon.Status.AVAILABLE.value,
            app_service_id=self.app_service2.id,
            owner_type=OwnerType.VO.value,
            user_id=self.user2.id,
            vo_id=vo1.id
        )
        coupon3.save(force_insert=True)

        # NotAuthenticated
        self.client.logout()
        url = reverse('wallet-api:admin-coupon-change-remark', kwargs={'id': 'notfound'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        # NotAuthenticated
        self.client.force_login(self.user)
        url = reverse('wallet-api:admin-coupon-change-remark', kwargs={'id': 'notfound'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # NoSuchCoupon
        url = reverse('wallet-api:admin-coupon-change-remark', kwargs={'id': 'notfound'})
        query = parse.urlencode(query={'remark': 'test remark'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='NoSuchCoupon', response=response)

        # AccessDenied
        url = reverse('wallet-api:admin-coupon-change-remark', kwargs={'id': coupon2.id})
        query = parse.urlencode(query={'remark': 'test remark'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # coupon2 ok, app_service1 admin
        coupon2.app_service.users.add(self.user)
        url = reverse('wallet-api:admin-coupon-change-remark', kwargs={'id': coupon2.id})
        query = parse.urlencode(query={'remark': 'test remark'})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['remark'], 'test remark')
        self.assertEqual(coupon2.remark, '')
        coupon2.refresh_from_db()
        self.assertEqual(coupon2.remark, 'test remark')

        # coupon3, AccessDenied
        url = reverse('wallet-api:admin-coupon-change-remark', kwargs={'id': coupon3.id})
        query = parse.urlencode(query={'remark': 'test remark66'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # coupon3 ok, federal admin
        self.user.set_federal_admin()
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['remark'], 'test remark66')
        self.assertEqual(coupon3.remark, '')
        coupon3.refresh_from_db()
        self.assertEqual(coupon3.remark, 'test remark66')
