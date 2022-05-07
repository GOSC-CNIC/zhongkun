from decimal import Decimal
from urllib import parse

from django.urls import reverse
from django.utils import timezone

from utils.model import OwnerType
from utils.test import get_or_create_service, get_or_create_user
from vo.models import VirtualOrganization, VoMember
from activity.models import CashCoupon
from . import set_auth_header, MyAPITestCase


class MeteringServerTests(MyAPITestCase):
    def setUp(self):
        self.user = set_auth_header(self)
        self.user2 = get_or_create_user(username='user2')
        self.service = get_or_create_service()
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user2
        )
        self.vo.save()

    def test_draw_cash_coupon(self):
        coupon1 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=timezone.now(),
            expiration_time = timezone.now(),
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
