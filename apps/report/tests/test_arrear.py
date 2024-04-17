import datetime
from urllib import parse
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone as dj_timezone

from apps.vo.models import VirtualOrganization
from apps.servers.models import ServiceConfig
from apps.storage.models import Bucket, ObjectsService
from apps.report.managers import (
    ArrearServerQueryOrderBy, ArrearServerManager,
    ArrearBucketQueryOrderBy, ArrearBucketManager
)
from utils.test import get_or_create_user, get_or_create_service, MyAPITestCase, get_or_create_storage_service
from utils.model import PayType, OwnerType


class ArrearServerTests(MyAPITestCase):
    def setUp(self):
        self.service1 = get_or_create_service()
        self.service2 = ServiceConfig(
            name='service2', org_data_center_id=self.service1.org_data_center_id,
            endpoint_url='service2', username='', password=''
        )
        self.service2.save(force_insert=True)

        self.user1 = get_or_create_user(username='lilei@xx.com')
        self.user2 = get_or_create_user(username='张三@xx.com')
        self.vo1 = VirtualOrganization(name='vo1', owner_id=self.user1.id)
        self.vo1.save(force_insert=True)
        self.vo2 = VirtualOrganization(name='vo2', owner_id=self.user2.id)
        self.vo2.save(force_insert=True)

    def init_bucket_data(self, nt: datetime.datetime):
        # user1, server(10.1.1.1), service1
        ArrearServerManager.create_arrear_server(
            server_id='server_id1', service_id=self.service1.id, service_name=self.service1.name,
            ipv4='10.1.1.1', ram_gib=4, vcpus=4, image='CentOS8', pay_type=PayType.POSTPAID.value,
            server_creation=nt - datetime.timedelta(days=100), server_expire=None,
            user_id=self.user1.id, username=self.user1.username, vo_id='', vo_name='', owner_type=OwnerType.USER.value,
            remark='test', date_=nt.date() - datetime.timedelta(days=31), balance_amount=Decimal('-100.11')
        )
        ArrearServerManager.create_arrear_server(
            server_id='server_id1', service_id=self.service1.id, service_name=self.service1.name,
            ipv4='10.1.1.1', ram_gib=4, vcpus=4, image='CentOS8', pay_type=PayType.POSTPAID.value,
            server_creation=nt - datetime.timedelta(days=100), server_expire=None,
            user_id=self.user1.id, username=self.user1.username, vo_id='', vo_name='', owner_type=OwnerType.USER.value,
            remark='test', date_=nt.date() - datetime.timedelta(days=10), balance_amount=Decimal('-121.11')
        )
        ArrearServerManager.create_arrear_server(
            server_id='server_id1', service_id=self.service1.id, service_name=self.service1.name,
            ipv4='10.1.1.1', ram_gib=4, vcpus=4, image='CentOS8', pay_type=PayType.POSTPAID.value,
            server_creation=nt - datetime.timedelta(days=100), server_expire=None,
            user_id=self.user1.id, username=self.user1.username, vo_id='', vo_name='', owner_type=OwnerType.USER.value,
            remark='test', date_=nt.date(), balance_amount=Decimal('-221.12')
        )

        # user2, server(159.1.12.66), service2
        ArrearServerManager.create_arrear_server(
            server_id='server_id2', service_id=self.service2.id, service_name=self.service2.name,
            ipv4='159.1.12.66', ram_gib=8, vcpus=2, image='Ubuntu', pay_type=PayType.PREPAID.value,
            server_creation=nt - datetime.timedelta(days=50), server_expire=nt - datetime.timedelta(days=12),
            user_id=self.user2.id, username=self.user2.username, vo_id='', vo_name='', owner_type=OwnerType.USER.value,
            remark='test', date_=nt.date() - datetime.timedelta(days=10), balance_amount=Decimal('-2.11')
        )
        ArrearServerManager.create_arrear_server(
            server_id='server_id2', service_id=self.service2.id, service_name=self.service2.name,
            ipv4='159.1.12.66', ram_gib=8, vcpus=2, image='Ubuntu', pay_type=PayType.PREPAID.value,
            server_creation=nt - datetime.timedelta(days=50), server_expire=nt - datetime.timedelta(days=12),
            user_id=self.user2.id, username=self.user2.username, vo_id='', vo_name='', owner_type=OwnerType.USER.value,
            remark='test', date_=nt.date(), balance_amount=Decimal('-21.12')
        )

        # vo1, server(223.19.12.88), service2
        ArrearServerManager.create_arrear_server(
            server_id='server_id3', service_id=self.service2.id, service_name=self.service2.name,
            ipv4='223.19.12.88', ram_gib=16, vcpus=6, image='Ubuntu2310', pay_type=PayType.POSTPAID.value,
            server_creation=nt - datetime.timedelta(days=40), server_expire=None,
            user_id=self.user2.id, username=self.user2.username, vo_id=self.vo1.id, vo_name=self.vo1.name,
            owner_type=OwnerType.VO.value,
            remark='测试test', date_=nt.date() - datetime.timedelta(days=10), balance_amount=Decimal('-2123.18')
        )
        ArrearServerManager.create_arrear_server(
            server_id='server_id3', service_id=self.service2.id, service_name=self.service2.name,
            ipv4='223.19.12.88', ram_gib=16, vcpus=6, image='Ubuntu2310', pay_type=PayType.POSTPAID.value,
            server_creation=nt - datetime.timedelta(days=40), server_expire=None,
            user_id=self.user2.id, username=self.user2.username, vo_id=self.vo1.id, vo_name=self.vo1.name,
            owner_type=OwnerType.VO.value,
            remark='测试test', date_=nt.date(), balance_amount=Decimal('-2423.18')
        )

        # vo2, server(223.19.12.169), service1
        ArrearServerManager.create_arrear_server(
            server_id='server_id4', service_id=self.service1.id, service_name=self.service2.name,
            ipv4='223.19.12.169', ram_gib=6, vcpus=2, image='CentOS7', pay_type=PayType.POSTPAID.value,
            server_creation=nt - datetime.timedelta(days=2), server_expire=None,
            user_id=self.user1.id, username=self.user1.username, vo_id=self.vo2.id, vo_name=self.vo2.name,
            owner_type=OwnerType.VO.value,
            remark='测试test', date_=nt.date(), balance_amount=Decimal('-123.18')
        )

    def test_list(self):
        nt = dj_timezone.now()
        self.init_bucket_data(nt=nt)

        url = reverse('report-api:admin-report-arrear-server-list')
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user1)
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)
        self.user1.set_federal_admin()

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'count', 'page_num', 'page_size', 'results'
        ], container=r.data)
        self.assertEqual(r.data['count'], 8)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 8)
        self.assertKeysIn(keys=[
            'id', 'server_id', 'service_id', 'service_name', 'ipv4', 'vcpus', 'ram', 'image', 'pay_type',
            'server_creation', 'server_expire', 'remarks', 'user_id', 'username', 'vo_id', 'vo_name',
            'owner_type', 'balance_amount', 'date', 'creation_time'
        ], container=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['balance_amount'], '-123.18')     # 默认按时间倒序

        # service_id
        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 4)
        self.assertEqual(r.data['results'][0]['balance_amount'], '-123.18')  # 默认按时间倒序

        # service_id, order_by
        query = parse.urlencode(query={
            'service_id': self.service1.id, 'order_by': ArrearServerQueryOrderBy.BALANCE_ASC.value})
        r = self.client.get(f'{url}?{query}')

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 4)
        self.assertEqual(r.data['results'][0]['ipv4'], '10.1.1.1')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-221.12')

        # service_id, page, page_size
        query = parse.urlencode(query={'service_id': self.service1.id, 'page': 2, 'page_size': 1})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(r.data['page_size'], 1)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(len(r.data['results']), 1)

        # service_id, date_start, date_end, order_by
        query = parse.urlencode(query={
            'service_id': self.service1.id,
            'date_start': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'date_end': nt.date().isoformat(),
            'order_by': ArrearServerQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['ipv4'], '10.1.1.1')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-121.11')
        self.assertEqual(r.data['results'][1]['ipv4'], '223.19.12.169')
        self.assertEqual(r.data['results'][1]['balance_amount'], '-123.18')
        self.assertEqual(r.data['results'][2]['ipv4'], '10.1.1.1')
        self.assertEqual(r.data['results'][2]['balance_amount'], '-221.12')

        query = parse.urlencode(query={
            'service_id': self.service1.id,
            'date_start': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'date_end': (nt - datetime.timedelta(days=1)).date().isoformat(),
            'order_by': ArrearServerQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['ipv4'], '10.1.1.1')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-121.11')

        # service_id, date_start, order_by
        query = parse.urlencode(query={
            'service_id': self.service1.id,
            'date_start': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'order_by': ArrearServerQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 3)

        # service_id, date_end, order_by
        query = parse.urlencode(query={
            'service_id': self.service1.id,
            'date_end': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'order_by': ArrearServerQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['ipv4'], '10.1.1.1')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-100.11')

        query = parse.urlencode(query={
            'service_id': self.service2.id,
            'date_end': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'order_by': ArrearServerQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={
            'service_id': self.service2.id,
            'date_end': (nt - datetime.timedelta(days=2)).date().isoformat(),
            'order_by': ArrearServerQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['ipv4'], '159.1.12.66')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-2.11')
        self.assertEqual(r.data['results'][1]['ipv4'], '223.19.12.88')
        self.assertEqual(r.data['results'][1]['balance_amount'], '-2123.18')

        # invalid date_start
        query = parse.urlencode(query={'date_start': '2023-06-1'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # invalid date_end
        query = parse.urlencode(query={'date_end': '2023-06'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'date_start': '2023-06-02', 'date_end': '2023-06-01'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # invalid order_by
        query = parse.urlencode(query={'order_by': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidOrderBy', response=r)


class ArrearBucketTests(MyAPITestCase):
    def setUp(self):
        self.service1 = get_or_create_storage_service()
        self.service2 = ObjectsService(
            name='service2', org_data_center_id=self.service1.org_data_center_id,
            endpoint_url='service2', username='', password=''
        )
        self.service2.save(force_insert=True)

        self.user1 = get_or_create_user(username='lilei@xx.com')
        self.user2 = get_or_create_user(username='张三@xx.com')
        self.vo1 = VirtualOrganization(name='vo1', owner_id=self.user1.id)
        self.vo1.save(force_insert=True)
        self.vo2 = VirtualOrganization(name='vo2', owner_id=self.user2.id)
        self.vo2.save(force_insert=True)

    def init_bucket_data(self, nt: datetime.datetime):
        # user1, bucket, service1
        ArrearBucketManager.create_arrear_bucket(
            bucket_id='bucket_id1', bucket_name='name-1', service_id=self.service1.id, service_name=self.service1.name,
            size_byte=123, object_count=4, bucket_creation=nt - datetime.timedelta(days=100), remarks='test',
            situation=Bucket.Situation.NORMAL.value, situation_time=nt,
            user_id=self.user1.id, username=self.user1.username,
            date_=nt.date() - datetime.timedelta(days=31), balance_amount=Decimal('-100.11')
        )
        ArrearBucketManager.create_arrear_bucket(
            bucket_id='bucket_id1', bucket_name='name-1', service_id=self.service1.id, service_name=self.service1.name,
            size_byte=123, object_count=4, bucket_creation=nt - datetime.timedelta(days=100), remarks='test',
            situation=Bucket.Situation.NORMAL.value, situation_time=nt,
            user_id=self.user1.id, username=self.user1.username,
            date_=nt.date() - datetime.timedelta(days=10), balance_amount=Decimal('-121.11')
        )
        ArrearBucketManager.create_arrear_bucket(
            bucket_id='bucket_id1', bucket_name='name-1', service_id=self.service1.id, service_name=self.service1.name,
            size_byte=123, object_count=4, bucket_creation=nt - datetime.timedelta(days=100), remarks='test',
            situation=Bucket.Situation.NORMAL.value, situation_time=nt,
            user_id=self.user1.id, username=self.user1.username,
            date_=nt.date(), balance_amount=Decimal('-221.12')
        )

        # user2, bucket, service2
        ArrearBucketManager.create_arrear_bucket(
            bucket_id='bucket_id2', bucket_name='name-2', service_id=self.service2.id, service_name=self.service2.name,
            size_byte=566123, object_count=34, bucket_creation=nt - datetime.timedelta(days=50), remarks='testqq',
            situation=Bucket.Situation.NORMAL.value, situation_time=nt,
            user_id=self.user2.id, username=self.user2.username,
            date_=nt.date() - datetime.timedelta(days=10), balance_amount=Decimal('-2.11')
        )
        ArrearBucketManager.create_arrear_bucket(
            bucket_id='bucket_id2', bucket_name='name-2', service_id=self.service2.id, service_name=self.service2.name,
            size_byte=1236766, object_count=64, bucket_creation=nt - datetime.timedelta(days=50), remarks='testqq',
            situation=Bucket.Situation.NORMAL.value, situation_time=nt,
            user_id=self.user2.id, username=self.user2.username,
            date_=nt.date(), balance_amount=Decimal('-21.12')
        )

        # vo1, bucket, service2
        ArrearBucketManager.create_arrear_bucket(
            bucket_id='bucket_id3', bucket_name='name-3', service_id=self.service2.id, service_name=self.service2.name,
            size_byte=0, object_count=0, bucket_creation=nt - datetime.timedelta(days=40), remarks='测试test',
            situation=Bucket.Situation.NORMAL.value, situation_time=None,
            user_id=self.user2.id, username=self.user2.username,
            date_=nt.date() - datetime.timedelta(days=10), balance_amount=Decimal('-2123.18')
        )
        ArrearBucketManager.create_arrear_bucket(
            bucket_id='bucket_id3', bucket_name='name-3', service_id=self.service2.id, service_name=self.service2.name,
            size_byte=46457223, object_count=120, bucket_creation=nt - datetime.timedelta(days=40), remarks='测试test',
            situation=Bucket.Situation.NORMAL.value, situation_time=None,
            user_id=self.user2.id, username=self.user2.username,
            date_=nt.date(), balance_amount=Decimal('-2423.18')
        )

        # vo2, bucket, service1
        ArrearBucketManager.create_arrear_bucket(
            bucket_id='bucket_id4', bucket_name='name-4', service_id=self.service1.id, service_name=self.service2.name,
            size_byte=64980, object_count=10, bucket_creation=nt - datetime.timedelta(days=2), remarks='测试test',
            situation=Bucket.Situation.NORMAL.value, situation_time=None,
            user_id=self.user1.id, username=self.user1.username,
            date_=nt.date(), balance_amount=Decimal('-123.18')
        )

    def test_list(self):
        nt = dj_timezone.now()
        self.init_bucket_data(nt=nt)

        url = reverse('report-api:admin-report-arrear-bucket-list')
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user1)
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)
        self.user1.set_federal_admin()

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'count', 'page_num', 'page_size', 'results'
        ], container=r.data)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['count'], 8)
        self.assertEqual(len(r.data['results']), 8)
        self.assertKeysIn(keys=[
            'id', 'bucket_id', 'bucket_name', 'service_id', 'service_name', 'size_byte', 'object_count',
            'bucket_creation', 'situation', 'situation_time', 'remarks', 'user_id', 'username',
            'balance_amount', 'date', 'creation_time'
        ], container=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['bucket_name'], 'name-4')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-123.18')     # 默认按时间倒序

        # service_id
        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 4)
        self.assertEqual(r.data['results'][0]['bucket_name'], 'name-4')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-123.18')  # 默认按时间倒序

        # service_id, order_by
        query = parse.urlencode(query={
            'service_id': self.service1.id, 'order_by': ArrearBucketQueryOrderBy.BALANCE_ASC.value})
        r = self.client.get(f'{url}?{query}')

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 4)
        self.assertEqual(r.data['results'][0]['bucket_name'], 'name-1')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-221.12')

        # service_id, page, page_size
        query = parse.urlencode(query={'service_id': self.service1.id, 'page': 2, 'page_size': 1})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['page_size'], 1)
        self.assertEqual(r.data['page_num'], 2)

        # service_id, date_start, date_end, order_by
        query = parse.urlencode(query={
            'service_id': self.service1.id,
            'date_start': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'date_end': nt.date().isoformat(),
            'order_by': ArrearBucketQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['bucket_name'], 'name-1')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-121.11')
        self.assertEqual(r.data['results'][1]['bucket_name'], 'name-4')
        self.assertEqual(r.data['results'][1]['balance_amount'], '-123.18')
        self.assertEqual(r.data['results'][2]['bucket_name'], 'name-1')
        self.assertEqual(r.data['results'][2]['balance_amount'], '-221.12')

        query = parse.urlencode(query={
            'service_id': self.service1.id,
            'date_start': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'date_end': (nt - datetime.timedelta(days=1)).date().isoformat(),
            'order_by': ArrearBucketQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['bucket_name'], 'name-1')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-121.11')

        # service_id, date_start, order_by
        query = parse.urlencode(query={
            'service_id': self.service1.id,
            'date_start': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'order_by': ArrearBucketQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)

        # service_id, date_end, order_by
        query = parse.urlencode(query={
            'service_id': self.service1.id,
            'date_end': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'order_by': ArrearBucketQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['bucket_name'], 'name-1')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-100.11')

        query = parse.urlencode(query={
            'service_id': self.service2.id,
            'date_end': (nt - datetime.timedelta(days=20)).date().isoformat(),
            'order_by': ArrearBucketQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 0)
        self.assertEqual(r.data['count'], 0)

        query = parse.urlencode(query={
            'service_id': self.service2.id,
            'date_end': (nt - datetime.timedelta(days=2)).date().isoformat(),
            'order_by': ArrearBucketQueryOrderBy.BALANCE_DESC.value})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['results'][0]['bucket_name'], 'name-2')
        self.assertEqual(r.data['results'][0]['balance_amount'], '-2.11')
        self.assertEqual(r.data['results'][1]['bucket_name'], 'name-3')
        self.assertEqual(r.data['results'][1]['balance_amount'], '-2123.18')

        # invalid date_start
        query = parse.urlencode(query={'date_start': '2023-06-31'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # invalid date_end
        query = parse.urlencode(query={'date_end': '2023-6'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'date_start': '2023-06-02', 'date_end': '2023-06-01'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # invalid order_by
        query = parse.urlencode(query={'order_by': 'testwew'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidOrderBy', response=r)
