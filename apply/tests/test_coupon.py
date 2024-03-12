from decimal import Decimal
from urllib import parse
from datetime import datetime, timedelta

from django.urls import reverse
from django.utils import timezone

from utils.model import OwnerType
from utils.time import utc
from utils.test import get_or_create_org_data_center, get_or_create_user, MyAPITestCase
from vo.models import VirtualOrganization
from apply.models import CouponApply
from apply.managers import CouponApplyManager


class CouponApplyTests(MyAPITestCase):
    def setUp(self):
        self.user1 = get_or_create_user()
        self.user2 = get_or_create_user(username='tom@cnic.cn')
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user1
        )
        self.vo.save()
        self.odc1 = get_or_create_org_data_center(name='odc1')
        self.odc2 = get_or_create_org_data_center(name='odc2')

    def test_list(self):
        apply1 = CouponApplyManager.create_apply(
            service_type=CouponApply.ServiceType.SERVER.value, odc=self.odc1,
            service_id='service_id1', service_name='service_name1', service_name_en='service_name_en1',
            pay_service_id='pay_service_id1', face_value=Decimal('1000.12'),
            expiration_time=datetime(year=2024, month=3, day=16, tzinfo=utc), apply_desc='申请原因2',
            user_id=self.user1.id, username=self.user1.username, vo_id='', vo_name='',
            owner_type=OwnerType.USER.value, creation_time=datetime(year=2022, month=6, day=16, tzinfo=utc)
        )
        apply2 = CouponApplyManager.create_apply(
            service_type=CouponApply.ServiceType.STORAGE.value, odc=self.odc1,
            service_id='service_id1', service_name='service_name1', service_name_en='service_name_en1',
            pay_service_id='pay_service_id1', face_value=Decimal('2000.12'),
            expiration_time=datetime(year=2024, month=3, day=16, tzinfo=utc), apply_desc='申请原因2',
            user_id=self.user1.id, username=self.user1.username, vo_id='', vo_name='',
            owner_type=OwnerType.USER.value, creation_time=datetime(year=2022, month=12, day=16, tzinfo=utc),
            status=CouponApply.Status.REJECT.value, reject_reason='不允许', approver='approver1'
        )
        apply3 = CouponApplyManager.create_apply(
            service_type=CouponApply.ServiceType.SERVER.value, odc=self.odc1,
            service_id='service_id1', service_name='service_name1', service_name_en='service_name_en1',
            pay_service_id='pay_service_id1', face_value=Decimal('3000.12'),
            expiration_time=datetime(year=2024, month=2, day=15, tzinfo=utc), apply_desc='申请原因3',
            user_id=self.user1.id, username=self.user1.username, vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value, creation_time=datetime(year=2023, month=5, day=8, tzinfo=utc)
        )
        apply4 = CouponApplyManager.create_apply(
            service_type=CouponApply.ServiceType.STORAGE.value, odc=self.odc1,
            service_id='service_id1', service_name='service_name1', service_name_en='service_name_en1',
            pay_service_id='pay_service_id1', face_value=Decimal('4000.12'),
            expiration_time=datetime(year=2023, month=11, day=15, tzinfo=utc), apply_desc='申请原因4',
            user_id=self.user1.id, username=self.user1.username, vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value, creation_time=datetime(year=2023, month=6, day=8, tzinfo=utc),
            status=CouponApply.Status.PASS.value, approver='approver1', approved_amount=Decimal('4000')
        )
        apply5 = CouponApplyManager.create_apply(
            service_type=CouponApply.ServiceType.SERVER.value, odc=self.odc2,
            service_id='service_id2', service_name='service_name2', service_name_en='service_name_en2',
            pay_service_id='pay_service_id2', face_value=Decimal('5000.12'),
            expiration_time=datetime(year=2023, month=12, day=15, tzinfo=utc), apply_desc='申请原因5',
            user_id=self.user1.id, username=self.user1.username, vo_id='', vo_name='',
            owner_type=OwnerType.USER.value, creation_time=datetime(year=2023, month=8, day=18, tzinfo=utc),
            status=CouponApply.Status.PASS.value, approver='approver1', approved_amount=Decimal('4000')
        )
        apply6 = CouponApplyManager.create_apply(
            service_type=CouponApply.ServiceType.SERVER.value, odc=self.odc2,
            service_id='service_id2', service_name='service_name2', service_name_en='service_name_en2',
            pay_service_id='pay_service_id2', face_value=Decimal('6000.12'),
            expiration_time=datetime(year=2023, month=12, day=15, tzinfo=utc), apply_desc='申请原因6',
            user_id=self.user2.id, username=self.user2.username, vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value, creation_time=datetime(year=2023, month=10, day=9, tzinfo=utc),
            status=CouponApply.Status.PENDING.value
        )
        apply7 = CouponApplyManager.create_apply(
            service_type=CouponApply.ServiceType.SCAN.value, odc=None,
            service_id='scan1', service_name='scan_name1', service_name_en='scan_name_en1',
            pay_service_id='pay_service_id6', face_value=Decimal('7000.12'),
            expiration_time=datetime(year=2024, month=3, day=15, tzinfo=utc), apply_desc='申请原因7',
            user_id=self.user1.id, username=self.user1.username, vo_id='', vo_name='',
            owner_type=OwnerType.USER.value, creation_time=datetime(year=2024, month=3, day=9, tzinfo=utc),
            status=CouponApply.Status.WAIT.value
        )
        apply8 = CouponApplyManager.create_apply(
            service_type=CouponApply.ServiceType.MONITOR_SITE.value, odc=None,
            service_id='site1', service_name='site_name1', service_name_en='site_name_en1',
            pay_service_id='pay_service_id8', face_value=Decimal('8000.12'),
            expiration_time=datetime(year=2024, month=12, day=15, tzinfo=utc), apply_desc='申请原因8',
            user_id=self.user2.id, username=self.user2.username, vo_id='', vo_name='',
            owner_type=OwnerType.USER.value, creation_time=datetime(year=2024, month=3, day=11, tzinfo=utc),
            status=CouponApply.Status.PENDING.value
        )

        # user1 list
        base_url = reverse('apply-api:coupon-list')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user2)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertKeysIn([
            'id', 'service_type', 'odc', 'service_id', 'service_name', 'service_name_en',
            'face_value', 'expiration_time', 'apply_desc', 'creation_time', 'update_time',
            'user_id', 'username', 'vo_id', 'vo_name', 'owner_type',
            'status', 'approver', 'approved_amount', 'reject_reason', 'coupon_id'], r.data['results'][0])
        self.assertEqual(r.data['results'][0]['id'], apply8.id)

        # vo
        query = parse.urlencode(query={'vo_id': self.vo.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # --- user1 test vo ---
        self.client.logout()
        self.client.force_login(self.user1)

        query = parse.urlencode(query={'vo_id': self.vo.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['id'], apply6.id)
        self.assertEqual(r.data['results'][1]['id'], apply4.id)
        self.assertEqual(r.data['results'][2]['id'], apply3.id)

        query = parse.urlencode(query={'vo_id': self.vo.id, 'service_type': CouponApply.ServiceType.SERVER.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], apply6.id)
        self.assertEqual(r.data['results'][1]['id'], apply3.id)

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'service_type': CouponApply.ServiceType.SERVER.value,
            'status': CouponApply.Status.PENDING.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], apply6.id)

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'time_start': '2023-06-01T00:00:00Z', 'time_end': '2023-07-06T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], apply4.id)

        # --- user1 test own ---
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 4)
        self.assertEqual(r.data['results'][0]['id'], apply7.id)
        self.assertEqual(r.data['results'][1]['id'], apply5.id)
        self.assertEqual(r.data['results'][2]['id'], apply2.id)
        self.assertEqual(r.data['results'][3]['id'], apply1.id)

        query = parse.urlencode(query={
            'time_start': '2023-01-01T00:00:00Z', 'time_end': '2023-12-06T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], apply5.id)

        query = parse.urlencode(query={'page_size': 2, 'page': 1})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], apply7.id)
        self.assertEqual(r.data['results'][1]['id'], apply5.id)

        query = parse.urlencode(query={'page_size': 3, 'page': 2})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], apply1.id)

        query = parse.urlencode(query={'status': CouponApply.Status.REJECT.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], apply2.id)

        # ---- test odc admin ---
        query = parse.urlencode(query={'as-admin': ''})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # odc1 admin
        self.odc1.users.add(self.user1)
        query = parse.urlencode(query={'as-admin': ''})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 4)
        self.assertEqual(r.data['results'][0]['id'], apply4.id)
        self.assertEqual(r.data['results'][1]['id'], apply3.id)
        self.assertEqual(r.data['results'][2]['id'], apply2.id)
        self.assertEqual(r.data['results'][3]['id'], apply1.id)

        # odc1 odc2 admin
        self.odc2.users.add(self.user1)
        query = parse.urlencode(query={'as-admin': ''})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 6)
        self.assertEqual(len(r.data['results']), 6)
        self.assertEqual(r.data['results'][0]['id'], apply6.id)
        self.assertEqual(r.data['results'][1]['id'], apply5.id)
        self.assertEqual(r.data['results'][2]['id'], apply4.id)
        self.assertEqual(r.data['results'][3]['id'], apply3.id)
        self.assertEqual(r.data['results'][4]['id'], apply2.id)
        self.assertEqual(r.data['results'][5]['id'], apply1.id)

        query = parse.urlencode(query={
            'as-admin': '', 'time_start': '2023-01-01T00:00:00Z', 'time_end': '2023-10-01T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['id'], apply5.id)
        self.assertEqual(r.data['results'][1]['id'], apply4.id)
        self.assertEqual(r.data['results'][2]['id'], apply3.id)

        self.odc1.users.remove(self.user1)
        self.odc2.users.remove(self.user1)

        # -- test fed admin ----
        query = parse.urlencode(query={'as-admin': ''})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user1.set_federal_admin()
        query = parse.urlencode(query={'as-admin': ''})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 8)
        self.assertEqual(len(r.data['results']), 8)
        self.assertEqual(r.data['results'][0]['id'], apply8.id)
        self.assertEqual(r.data['results'][1]['id'], apply7.id)

        query = parse.urlencode(query={'as-admin': '', 'vo_id': self.vo.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['id'], apply6.id)
        self.assertEqual(r.data['results'][1]['id'], apply4.id)
        self.assertEqual(r.data['results'][2]['id'], apply3.id)

        query = parse.urlencode(query={
            'as-admin': '', 'time_start': '2023-01-01T00:00:00Z', 'time_end': '2024-3-09T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 5)
        self.assertEqual(len(r.data['results']), 5)
        self.assertEqual(r.data['results'][0]['id'], apply7.id)
        self.assertEqual(r.data['results'][1]['id'], apply6.id)
        self.assertEqual(r.data['results'][2]['id'], apply5.id)
        self.assertEqual(r.data['results'][3]['id'], apply4.id)
        self.assertEqual(r.data['results'][4]['id'], apply3.id)

        query = parse.urlencode(query={
            'as-admin': '', 'time_start': '2023-01-01T00:00:00Z', 'time_end': '2024-3-09T00:00:00Z',
            'status': CouponApply.Status.WAIT.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], apply7.id)
        self.assertEqual(r.data['results'][1]['id'], apply3.id)

        query = parse.urlencode(query={
            'as-admin': '', 'time_start': '2023-01-01T00:00:00Z', 'time_end': '2024-3-09T00:00:00Z',
            'status': CouponApply.Status.WAIT.value, 'service_type': CouponApply.ServiceType.SCAN.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], apply7.id)
