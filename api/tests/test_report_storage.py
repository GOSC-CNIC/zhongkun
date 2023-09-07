import datetime
from urllib import parse
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from storage.models import Bucket, ObjectsService
from report.models import BucketStatsMonthly
from report.managers import BktStatsMonthQueryOrderBy
from utils.test import get_or_create_user, get_or_create_storage_service
from . import MyAPITestCase


def create_bucket_monthly_ins(
        _date, service_id: str, bucket_id: str, bucket_name: str, size_byte: int, increment_byte: int,
        object_count: int, original_amount: Decimal, increment_amount: Decimal, user
):
    user_id = username = ''
    if user:
        user_id = user.id
        username = user.username

    ins = BucketStatsMonthly(
        service_id=service_id,
        bucket_id=bucket_id,
        bucket_name=bucket_name,
        size_byte=size_byte,
        increment_byte=increment_byte,
        object_count=object_count,
        original_amount=original_amount,
        increment_amount=increment_amount,
        user_id=user_id, username=username,
        date=_date, creation_time=timezone.now()
    )
    ins.save(force_insert=True)
    return ins


class BucketStatsMonthlyTests(MyAPITestCase):
    def setUp(self):
        self.service1 = get_or_create_storage_service()
        self.user1 = get_or_create_user(username='lilei@xx.com')
        self.user2 = get_or_create_user(username='张三@xx.com')

    @staticmethod
    def create_stats_monthly_for_bucket(bkt: Bucket, months: list):
        months.sort()
        for m in months:
            _date = datetime.date(year=2023, month=m, day=1)
            create_bucket_monthly_ins(
                _date=_date, service_id=bkt.service_id, bucket_id=bkt.id, bucket_name=bkt.name,
                size_byte=m*5, increment_byte=m*2,
                object_count=m+1, original_amount=Decimal(f'{m*10}'), increment_amount=Decimal(f'{m}'), user=bkt.user
            )

    def test_list_bucket_stats(self):
        service1 = self.service1
        service2 = ObjectsService(
            name='service2', data_center_id=self.service1.data_center.id,
            endpoint_url='service2', username='', password=''
        )
        service2.save(force_insert=True)

        u1_b1 = Bucket(name='bucket1', service_id=service1.id, user_id=self.user1.id,
                       creation_time=timezone.now(), storage_size=1000, object_count=10)
        u1_b1.save(force_insert=True)
        u1_b2 = Bucket(name='bucket2', service_id=service1.id, user_id=self.user1.id,
                       creation_time=timezone.now(), storage_size=2000, object_count=20)
        u1_b2.save(force_insert=True)
        u2_b3 = Bucket(name='bucket4', service_id=service1.id, user_id=self.user2.id,
                       creation_time=timezone.now(), storage_size=4000, object_count=40)
        u2_b3.save(force_insert=True)

        self.create_stats_monthly_for_bucket(bkt=u1_b1, months=list(range(1, 8)))   # 1-7
        self.create_stats_monthly_for_bucket(bkt=u1_b2, months=list(range(3, 10)))  # 3-9
        self.create_stats_monthly_for_bucket(bkt=u2_b3, months=list(range(6, 13)))  # 6-12

        url = reverse('api:report-bucket-stats-monthly-list')
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user1)
        # user1
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'count', 'page_num', 'page_size', 'results'
        ], container=r.data)
        self.assertEqual(r.data['count'], 7 + 7)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 7 + 7)
        self.assertKeysIn(keys=[
            'id', 'service', 'bucket_id', 'bucket_name', 'size_byte', 'increment_byte', 'object_count',
            'original_amount', 'increment_amount', 'user_id', 'username', 'date', 'creation_time'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=r.data['results'][0]['service'])

        # bucket_id
        query = parse.urlencode(query={'bucket_id': u1_b1.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 7)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 7)

        # bucket_id, page, page_size
        query = parse.urlencode(query={'bucket_id': u1_b1.id, 'page': 2, 'page_size': 1})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 7)
        self.assertEqual(r.data['page_size'], 1)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(len(r.data['results']), 1)
        ins = r.data['results'][0]  # b1 6月
        month = 6
        self.assertEqual(ins['bucket_id'], u1_b1.id)
        self.assertEqual(ins['size_byte'], month * 5)
        self.assertEqual(ins['increment_byte'], month * 2)
        self.assertEqual(Decimal(ins['original_amount']), Decimal(f'{month * 10}'))
        self.assertEqual(Decimal(ins['increment_amount']), Decimal(f'{month}'))
        self.assertEqual(ins['object_count'], month + 1)

        # bucket_id, date_start, date_end, order_by
        query = parse.urlencode(query={
            'bucket_id': u1_b1.id, 'date_start': '2023-05', 'date_end': '2023-08',
            'order_by': BktStatsMonthQueryOrderBy.DATE_ASC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 3)
        ins = r.data['results'][0]  # b1 5月
        month = 5
        self.assertEqual(ins['bucket_id'], u1_b1.id)
        self.assertEqual(ins['size_byte'], month * 5)
        self.assertEqual(ins['increment_byte'], month * 2)
        self.assertEqual(Decimal(ins['original_amount']), Decimal(f'{month * 10}'))
        self.assertEqual(Decimal(ins['increment_amount']), Decimal(f'{month}'))
        self.assertEqual(ins['object_count'], month + 1)

        # bucket_id, date_start, date_end, order_by
        query = parse.urlencode(query={
            'bucket_id': u1_b1.id, 'date_start': '2023-06', 'date_end': '2023-08',
            'order_by': BktStatsMonthQueryOrderBy.DATE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 2)
        ins = r.data['results'][0]  # b1 7月
        month = 7
        self.assertEqual(ins['bucket_id'], u1_b1.id)
        self.assertEqual(ins['size_byte'], month * 5)
        self.assertEqual(ins['increment_byte'], month * 2)
        self.assertEqual(Decimal(ins['original_amount']), Decimal(f'{month * 10}'))
        self.assertEqual(Decimal(ins['increment_amount']), Decimal(f'{month}'))
        self.assertEqual(ins['object_count'], month + 1)

        # bucket_id, date_start, date_end
        query = parse.urlencode(query={
            'bucket_id': u1_b2.id, 'date_start': '2023-06', 'date_end': '2023-06',
            'order_by': BktStatsMonthQueryOrderBy.DATE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 1)
        ins = r.data['results'][0]  # b2 6月
        self.assertEqual(ins['date'], '2023-06')

        # bucket_id, date_start
        query = parse.urlencode(query={
            'bucket_id': u1_b2.id, 'date_start': '2023-06',
            'order_by': BktStatsMonthQueryOrderBy.DATE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 4)

        # invalid date_start
        query = parse.urlencode(query={'date_start': '2023-06-01'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # invalid date_end
        query = parse.urlencode(query={'date_end': '2023-06-01'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'date_start': '2023-07', 'date_end': '2023-06'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # invalid order_by
        query = parse.urlencode(query={'order_by': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidOrderBy', response=r)

        # user1 list user2 b3
        query = parse.urlencode(query={'bucket_id': u2_b3.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 0)

        # ----- admin -------
        query = parse.urlencode(query={'as-admin': ''})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user1.set_federal_admin()
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 7 + 7 + 7)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 21)

        # bucket_id, date_start, date_end, order_by
        query = parse.urlencode(query={
            'bucket_id': u2_b3.id, 'date_start': '2023-06', 'date_end': '2023-08', 'as-admin': '',
            'order_by': BktStatsMonthQueryOrderBy.INCR_SIZE_ASC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 3)
        ins = r.data['results'][0]  # b3 6月
        month = 6
        self.assertEqual(ins['bucket_id'], u2_b3.id)
        self.assertEqual(ins['size_byte'], month * 5)
        self.assertEqual(ins['increment_byte'], month * 2)
        self.assertEqual(Decimal(ins['original_amount']), Decimal(f'{month * 10}'))
        self.assertEqual(Decimal(ins['increment_amount']), Decimal(f'{month}'))
        self.assertEqual(ins['object_count'], month + 1)

        query = parse.urlencode(query={
            'bucket_id': u2_b3.id, 'date_start': '2023-06', 'date_end': '2023-08', 'as-admin': '',
            'order_by': BktStatsMonthQueryOrderBy.INCR_SIZE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        ins = r.data['results'][0]  # b3 8月
        month = 8
        self.assertEqual(ins['bucket_id'], u2_b3.id)
        self.assertEqual(ins['size_byte'], month * 5)
        self.assertEqual(ins['increment_byte'], month * 2)
        self.assertEqual(Decimal(ins['original_amount']), Decimal(f'{month * 10}'))
        self.assertEqual(Decimal(ins['increment_amount']), Decimal(f'{month}'))
        self.assertEqual(ins['object_count'], month + 1)
