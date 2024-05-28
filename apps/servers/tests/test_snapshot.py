from datetime import timedelta, datetime
from urllib import parse
from urllib.parse import urlencode
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from utils.test import get_or_create_user, get_or_create_service, MyAPITransactionTestCase
from utils.model import PayType, OwnerType, ResourceType
from utils.decimal_utils import quantize_10_2
from apps.order.models import Order, Price
from apps.order.managers import OrderManager, ServerSnapshotConfig
from apps.vo.models import VirtualOrganization, VoMember
from apps.servers.managers import ServerSnapshotManager
from apps.servers.models import ServiceConfig, ServerSnapshot, Server
from apps.servers.tests import create_server_metadata


class ServerSnapshotTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = get_or_create_user(username='user2')
        self.service = get_or_create_service()
        self.vo = VirtualOrganization(name='test vo', owner=self.user2)
        self.vo.save(force_insert=True)
        self.price = Price(
            vm_ram=Decimal('0.012'),
            vm_cpu=Decimal('0.066'),
            vm_disk=Decimal('0.122'),
            vm_pub_ip=Decimal('0.66'),
            vm_upstream=Decimal('0.33'),
            vm_downstream=Decimal('1.44'),
            vm_disk_snap=Decimal('0.65'),
            disk_size=Decimal('1.02'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            prepaid_discount=66
        )
        self.price.save(force_insert=True)

    def test_list_disk(self):
        service2 = ServiceConfig(
            name='test2', name_en='test2_en', org_data_center=self.service.org_data_center
        )
        service2.save(force_insert=True)

        server1 = create_server_metadata(
            service=self.service, user=self.user, ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )
        snapshot1 = ServerSnapshotManager.create_snapshot_metadata(
            name='name1', size_dib=66, remarks='snapshot1 test', instance_id='11',
            creation_time=timezone.now(), expiration_time=timezone.now()-timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user, vo=None,
            server=server1, service=server1.service
        )
        snapshot2 = ServerSnapshotManager.create_snapshot_metadata(
            name='name2', size_dib=88, remarks='snapshot2 test', instance_id='22',
            creation_time=timezone.now(), expiration_time=timezone.now() + timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user, vo=None,
            server=None, service=service2
        )
        snapshot3_vo = ServerSnapshotManager.create_snapshot_metadata(
            name='name3', size_dib=886, remarks='vo snapshot3 test', instance_id='33',
            creation_time=timezone.now(), expiration_time=None,
            start_time=None, pay_type=PayType.POSTPAID.value,
            classification=ServerSnapshot.Classification.VO.value, user=self.user2, vo=self.vo,
            server=server1, service=server1.service
        )
        snapshot4_vo = ServerSnapshotManager.create_snapshot_metadata(
            name='name4', size_dib=286, remarks='vo snapshot4 test', instance_id='44',
            creation_time=timezone.now(), expiration_time=timezone.now() + timedelta(days=10),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.VO.value, user=self.user, vo=self.vo,
            server=None, service=service2
        )
        snapshot4_vo.server_id = 'missing'
        snapshot4_vo.save(update_fields=['server_id'])
        snapshot4_vo.server = None

        base_url = reverse('servers-api:server-snapshot-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        # ----  Bad -----------
        # query 'user_id' only as-admin
        query_str = parse.urlencode(query={'user_id': 'c'})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query 'vo_name' only as-admin
        query_str = parse.urlencode(query={'vo_name': 'c'})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query 'username' only as-admin
        query_str = parse.urlencode(query={'username': 'c'})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query 'exclude_vo' only as-admin
        query_str = parse.urlencode(query={'exclude_vo': None})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        #  -------------- user --------------
        # list user
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertKeysIn(['id', 'name', 'size', 'remarks', 'creation_time', 'expiration_time', 'pay_type',
                           'classification', 'user', 'vo', 'server', 'service'], response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['service'])
        self.assertKeysIn(['id', 'username'], response.data['results'][0]['user'])
        self.assertIsNone(response.data['results'][0]['vo'])
        self.assertEqual(response.data['results'][0]['id'], snapshot2.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot1.id)
        self.assertKeysIn(['id', 'vcpus', 'ram_gib', 'ipv4', 'image', 'creation_time', 'expiration_time',
                           'remarks'], response.data['results'][1]['server'])
        self.assertIsNone(response.data['results'][0]['server'])

        # service_id
        query = urlencode(query={'service_id': self.service.id, 'page_size': 10})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 10)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot1.id)

        # page, page_size
        query = urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot1.id)
        self.assertEqual(response.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(response.data['results'][0]['user']['username'], self.user.username)

        # param "remark
        query = parse.urlencode({'remark': 'snapshot1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot1.id)

        query = parse.urlencode({'remark': 'snapshot2 test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot2.id)

        # -------- vo ----------
        # list vo
        query = urlencode(query={'vo_id': 2, 'page_size': 100})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        query = urlencode(query={'vo_id': self.vo.id, 'page_size': 100})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value).save()

        query = urlencode(query={'vo_id': self.vo.id, 'page_size': 100})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], snapshot4_vo.id)
        self.assertEqual(response.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(response.data['results'][0]['user']['username'], self.user.username)
        self.assertEqual(response.data['results'][0]['vo']['id'], self.vo.id)
        self.assertEqual(response.data['results'][0]['vo']['name'], self.vo.name)

        # service_id
        query = urlencode(query={'vo_id': self.vo.id, 'service_id': self.service.id, 'page_size': 10})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 10)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot3_vo.id)

        query = urlencode(query={'vo_id': self.vo.id, 'service_id': service2.id, 'page_size': 10})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 10)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot4_vo.id)

        # param "remark
        query = parse.urlencode(query={'vo_id': self.vo.id, 'remark': 'vo'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], snapshot4_vo.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot3_vo.id)

        query = parse.urlencode(query={'vo_id': self.vo.id, 'remark': 'snapshot2'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        #  -------------  service admin ------------------
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 0)

        # service1 admin
        self.service.users.add(self.user)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertKeysIn(['id', 'name', 'size', 'remarks', 'creation_time', 'expiration_time', 'pay_type',
                           'classification', 'user', 'vo', 'server', 'service'], response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['service'])
        self.assertKeysIn(['id', 'username'], response.data['results'][0]['user'])
        self.assertEqual(response.data['results'][0]['id'], snapshot3_vo.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot1.id)
        self.assertKeysIn(['id', 'vcpus', 'ram_gib', 'ipv4', 'image', 'creation_time', 'expiration_time',
                           'remarks'], response.data['results'][1]['server'])

        # service_id
        query = urlencode(query={'as-admin': '', 'service_id': self.service.id, 'page_size': 10})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_size'], 10)
        self.assertEqual(response.data['results'][0]['id'], snapshot3_vo.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot1.id)

        query = urlencode(query={'as-admin': '', 'service_id': service2.id, 'page_size': 10})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 403)

        service2.users.add(self.user)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)

        # --- org data center admin ----
        service2.users.remove(self.user)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        # 数据中心管理员
        service2.org_data_center.add_admin_user(self.user)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)

        # -------------- federal_admin ----------------
        self.service.users.remove(self.user)
        service2.users.remove(self.user)
        service2.org_data_center.remove_admin_user(self.user)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        self.user.set_federal_admin()
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)

        # page, page_size
        query = urlencode(query={'as-admin': '', 'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot3_vo.id)

        # param "remark
        query = parse.urlencode({'as-admin': '', 'remark': 'snapshot1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot1.id)

        query = parse.urlencode({'as-admin': '', 'remark': 'vo'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['id'], snapshot4_vo.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot3_vo.id)

        # query "exclude_vo"
        query_str = parse.urlencode(query={'as-admin': '', 'exclude_vo': ''})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], snapshot2.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot1.id)

        # query "username"
        query_str = parse.urlencode(query={'as-admin': '', 'username': self.user2.username})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot3_vo.id)

        # query "username" and "exclude_vo"
        query_str = parse.urlencode(query={'as-admin': '', 'username': self.user2.username, 'exclude_vo': ''})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query_str = parse.urlencode(query={'as-admin': '', 'username': self.user.username, 'exclude_vo': ''})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], snapshot2.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot1.id)

        # query "user_id"
        query_str = parse.urlencode(query={'as-admin': '', 'user_id': self.user.id})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)

        # query "user_id" and "exclude_vo"
        query_str = parse.urlencode(query={'as-admin': '', 'user_id': self.user.id, 'exclude_vo': ''})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], snapshot2.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot1.id)

        # query "user_id"
        query_str = parse.urlencode(query={'as-admin': '', 'user_id': self.user2.id})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot3_vo.id)

        # query "vo_id"
        query_str = parse.urlencode(query={'as-admin': '', 'vo_id': self.vo.id})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], snapshot4_vo.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot3_vo.id)

        # query "vo_id" and "user_id"
        query_str = parse.urlencode(query={'as-admin': '', 'vo_id': self.vo.id, 'user_id': self.user.id})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot4_vo.id)

        query_str = parse.urlencode(query={'as-admin': '', 'vo_id': self.vo.id, 'user_id': self.user2.id})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], snapshot3_vo.id)

        # query "vo_name"
        query_str = parse.urlencode(query={'as-admin': '', 'vo_name': self.vo.name})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], snapshot4_vo.id)
        self.assertEqual(response.data['results'][1]['id'], snapshot3_vo.id)

        # query "vo_id" and "exclude_vo"
        query_str = parse.urlencode(query={'as-admin': '', 'vo_id': self.vo.id, 'exclude_vo': ''})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 400)

        # query "vo_name" and "exclude_vo"
        query_str = parse.urlencode(query={'as-admin': '', 'vo_name': 'sss', 'exclude_vo': ''})
        response = self.client.get(f'{base_url}?{query_str}')
        self.assertEqual(response.status_code, 400)

    def test_detail(self):
        server1 = create_server_metadata(
            service=self.service, user=self.user, ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )
        snapshot1 = ServerSnapshotManager.create_snapshot_metadata(
            name='name1', size_dib=66, remarks='snapshot1 test', instance_id='11',
            creation_time=timezone.now(), expiration_time=timezone.now() - timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user, vo=None,
            server=server1, service=server1.service
        )
        snapshot2 = ServerSnapshotManager.create_snapshot_metadata(
            name='name2', size_dib=88, remarks='snapshot2 test', instance_id='22',
            creation_time=timezone.now(), expiration_time=timezone.now() + timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user, vo=None,
            server=None, service=self.service
        )
        snapshot3_vo = ServerSnapshotManager.create_snapshot_metadata(
            name='name3', size_dib=886, remarks='vo snapshot3 test', instance_id='33',
            creation_time=timezone.now(), expiration_time=timezone.now() + timedelta(days=11),
            start_time=None, pay_type=PayType.POSTPAID.value,
            classification=ServerSnapshot.Classification.VO.value, user=self.user2, vo=self.vo,
            server=server1, service=server1.service
        )
        snapshot3_vo.server_id = 'afafa'
        snapshot3_vo.save(update_fields=['server_id'])

        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': 'test'})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': 'test'})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # detail user
        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': snapshot1.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'size', 'remarks', 'creation_time', 'expiration_time', 'pay_type',
                           'classification', 'user', 'vo', 'server', 'service'], response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['service'])
        self.assertKeysIn(['id', 'username'], response.data['user'])
        self.assertEqual(response.data['id'], snapshot1.id)
        self.assertKeysIn(['id', 'vcpus', 'ram_gib', 'ipv4', 'image', 'creation_time', 'expiration_time',
                           'remarks'], response.data['server'])

        # detail vo disk
        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': snapshot3_vo.id})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value).save()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'size', 'remarks', 'creation_time', 'expiration_time', 'pay_type',
                           'classification', 'user', 'vo', 'server', 'service'], response.data)
        self.assertEqual(response.data['id'], snapshot3_vo.id)
        self.assertIsNone(response.data['server'])

        # --- test service admin ---
        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': snapshot3_vo.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.users.add(self.user)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'size', 'remarks', 'creation_time', 'expiration_time', 'pay_type',
                           'classification', 'user', 'vo', 'server', 'service'], response.data)
        self.assertEqual(response.data['id'], snapshot3_vo.id)

        # --- test odc admin ---
        self.service.users.remove(self.user)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.org_data_center.users.add(self.user)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'size', 'remarks', 'creation_time', 'expiration_time', 'pay_type',
                           'classification', 'user', 'vo', 'server', 'service'], response.data)
        self.assertEqual(response.data['id'], snapshot3_vo.id)

        # --- test fed admin ---
        self.service.org_data_center.users.remove(self.user)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'size', 'remarks', 'creation_time', 'expiration_time', 'pay_type',
                           'classification', 'user', 'vo', 'server', 'service'], response.data)
        self.assertEqual(response.data['id'], snapshot3_vo.id)

    def test_delete(self):
        server1 = create_server_metadata(
            service=self.service, user=self.user, ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )
        snapshot1 = ServerSnapshotManager.create_snapshot_metadata(
            name='name1', size_dib=66, remarks='snapshot1 test', instance_id='99999999123456789',   # 避免误删真实快照
            creation_time=timezone.now(), expiration_time=timezone.now() - timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user, vo=None,
            server=server1, service=server1.service
        )
        snapshot2 = ServerSnapshotManager.create_snapshot_metadata(
            name='name2', size_dib=88, remarks='snapshot2 test', instance_id='99999999123456789',
            creation_time=timezone.now(), expiration_time=timezone.now() + timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user, vo=None,
            server=None, service=self.service
        )
        snapshot3_vo = ServerSnapshotManager.create_snapshot_metadata(
            name='name3', size_dib=886, remarks='vo snapshot3 test', instance_id='99999999123456789',
            creation_time=timezone.now(), expiration_time=timezone.now() + timedelta(days=11),
            start_time=None, pay_type=PayType.POSTPAID.value,
            classification=ServerSnapshot.Classification.VO.value, user=self.user2, vo=self.vo,
            server=server1, service=server1.service
        )
        snapshot3_vo.server_id = 'afafa'
        snapshot3_vo.save(update_fields=['server_id'])

        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': 'test'})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': 'test'})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # user
        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': snapshot1.id})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        snapshot1.refresh_from_db()
        self.assertTrue(snapshot1.deleted)
        self.assertEqual(snapshot1.deleted_user, self.user.username)

        # vo
        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': snapshot3_vo.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value).save()

        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        snapshot3_vo.refresh_from_db()
        self.assertTrue(snapshot3_vo.deleted)
        self.assertEqual(snapshot3_vo.deleted_user, self.user.username)

        # --- test service admin ---
        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': snapshot2.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.delete(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.users.add(self.user)
        response = self.client.delete(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 204)
        snapshot2.refresh_from_db()
        self.assertTrue(snapshot2.deleted)
        self.assertEqual(snapshot2.deleted_user, self.user.username)

        # --- test odc admin ---
        self.service.users.remove(self.user)
        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': snapshot2.id})
        response = self.client.delete(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        snapshot2.deleted = False
        snapshot2.deleted_user = ''
        snapshot2.save(update_fields=['deleted', 'deleted_user'])
        response = self.client.delete(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.org_data_center.users.add(self.user)
        response = self.client.delete(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 204)
        snapshot2.refresh_from_db()
        self.assertTrue(snapshot2.deleted)
        self.assertEqual(snapshot2.deleted_user, self.user.username)

        # --- test fed admin ---
        self.service.org_data_center.users.remove(self.user)
        snapshot3_vo.deleted = False
        snapshot3_vo.deleted_user = ''
        snapshot3_vo.save(update_fields=['deleted', 'deleted_user'])
        base_url = reverse('servers-api:server-snapshot-detail', kwargs={'id': snapshot3_vo.id})
        response = self.client.delete(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
        response = self.client.delete(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 204)
        snapshot3_vo.refresh_from_db()
        self.assertTrue(snapshot3_vo.deleted)
        self.assertEqual(snapshot3_vo.deleted_user, self.user.username)

    def test_rollback(self):
        server1 = create_server_metadata(
            service=self.service, user=self.user2, ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )
        server1.lock = Server.Lock.OPERATION.value
        server1.save(update_fields=['lock'])
        server2_vo = create_server_metadata(
            service=self.service, user=self.user, vo_id=self.vo.id, classification='vo',
            ram=8, vcpus=6, default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )
        snapshot1 = ServerSnapshotManager.create_snapshot_metadata(
            name='name1', size_dib=66, remarks='snapshot1 test', instance_id='99999999123456789',
            creation_time=timezone.now(), expiration_time=timezone.now() - timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user2, vo=None,
            server=server1, service=server1.service
        )
        snapshot2_vo = ServerSnapshotManager.create_snapshot_metadata(
            name='name1', size_dib=66, remarks='snapshot1 test', instance_id='99999999123456789',
            creation_time=timezone.now(), expiration_time=timezone.now() - timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.VO.value, user=self.user, vo=self.vo,
            server=server2_vo, service=server2_vo.service
        )

        base_url = reverse('servers-api:server-snapshot-rollback', kwargs={'id': 'test', 'server_id': 'server_id'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        base_url = reverse('servers-api:server-snapshot-rollback', kwargs={'id': 'test', 'server_id': 'server_id'})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # user
        base_url = reverse('servers-api:server-snapshot-rollback',
                           kwargs={'id': snapshot1.id, 'server_id': 'server_id'})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        base_url = reverse('servers-api:server-snapshot-rollback',
                           kwargs={'id': snapshot1.id, 'server_id': server1.id})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo
        base_url = reverse('servers-api:server-snapshot-rollback',
                           kwargs={'id': snapshot2_vo.id, 'server_id': server2_vo.id})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value).save()
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 500)

        # 快照不属于云主机
        base_url = reverse('servers-api:server-snapshot-rollback',
                           kwargs={'id': snapshot1.id, 'server_id': server2_vo.id})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # user2
        self.client.logout()
        self.client.force_login(self.user2)

        base_url = reverse('servers-api:server-snapshot-rollback',
                           kwargs={'id': snapshot1.id, 'server_id': server1.id})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

    def test_create(self):
        server1 = create_server_metadata(
            service=self.service, user=self.user, ram=8, vcpus=6, disk_size=0,
            default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )
        vo_server = create_server_metadata(
            service=self.service, user=self.user, vo_id=self.vo.id,
            ram=8, vcpus=6, disk_size=128, classification=Server.Classification.VO.value,
            default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )

        base_url = reverse('servers-api:server-snapshot-list')
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user2)

        # period
        response = self.client.post(base_url, data={
            'server_id': 'server_id',
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        response = self.client.post(base_url, data={
            'server_id': 'server_id',
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 'period',
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        response = self.client.post(base_url, data={
            'server_id': 'server_id',
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 0,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)

        # period_unit
        response = self.client.post(base_url, data={
            'server_id': 'server_id',
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 1,
        })
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        response = self.client.post(base_url, data={
            'server_id': 'server_id',
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 1,
            'period_unit': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidPeriodUnit', response=response)

        # period and period_unit， 最大时长五年
        response = self.client.post(base_url, data={
            'server_id': 'server_id',
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 12 * 5 + 1,
            'period_unit': Order.PeriodUnit.MONTH.value
        })
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)
        response = self.client.post(base_url, data={
            'server_id': 'server_id',
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 30 * 12 * 5 + 1,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)

        # server_id
        response = self.client.post(base_url, data={
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 1,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        response = self.client.post(base_url, data={
            'server_id': 'server_id',
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 1,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        response = self.client.post(base_url, data={
            'server_id': server1.id,
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 1,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # user，服务单元结算单元id无效
        self.client.logout()
        self.client.force_login(self.user)
        response = self.client.post(base_url, data={
            'server_id': server1.id,
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 1,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)
        server1.service.pay_app_service_id = 'test'
        server1.service.save(update_fields=['pay_app_service_id'])

        # 系统盘大小未知
        response = self.client.post(base_url, data={
            'server_id': server1.id,
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 1,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        self.assertEqual(Order.objects.count(), 0)
        server1.disk_size = 100
        server1.save(update_fields=['disk_size'])
        response = self.client.post(base_url, data={
            'server_id': server1.id,
            'snapshot_name': 'snapshot_name',
            'description': 'description',
            'period': 1,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertEqual(response.status_code, 200)
        order1_id = response.data['order_id']
        self.assertEqual(Order.objects.count(), 1)
        order1, resources1 = OrderManager().get_order_detail(order_id=order1_id, user=self.user)
        self.assertEqual(resources1[0].instance_status, resources1[0].InstanceStatus.WAIT.value)
        self.assertEqual(resources1[0].instance_remark, 'description')
        self.assertEqual(order1.trading_status, order1.TradingStatus.OPENING.value)
        self.assertEqual(order1.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order1.resource_type, ResourceType.VM_SNAPSHOT.value)
        self.assertEqual(order1.owner_type, OwnerType.USER.value)
        self.assertEqual(order1.user_id, self.user.id)
        self.assertEqual(order1.period, 1)
        self.assertEqual(order1.period_unit, Order.PeriodUnit.DAY.value)

        original_price = self.price.vm_disk_snap * 100 * 24 * 1
        trade_price = original_price * Decimal.from_float(self.price.prepaid_discount / 100)
        self.assertEqual(order1.total_amount, quantize_10_2(original_price))
        self.assertEqual(order1.payable_amount, quantize_10_2(trade_price))
        cfg = ServerSnapshotConfig.from_dict(order1.instance_config)
        self.assertEqual(cfg.server_id, server1.id)
        self.assertEqual(cfg.systemdisk_size, 100)
        self.assertEqual(cfg.snapshot_name, 'snapshot_name')
        self.assertEqual(cfg.snapshot_desc, 'description')

        server1.disk_size = 200
        server1.save(update_fields=['disk_size'])
        response = self.client.post(base_url, data={
            'server_id': server1.id,
            'snapshot_name': 'snapshot_name1',
            'description': 'tes的歌曲',
            'period': 2,
            'period_unit': Order.PeriodUnit.MONTH.value
        })
        self.assertEqual(response.status_code, 200)
        order2_id = response.data['order_id']
        self.assertEqual(Order.objects.count(), 2)
        order2, resources2 = OrderManager().get_order_detail(order_id=order2_id, user=self.user)
        self.assertEqual(resources2[0].instance_status, resources2[0].InstanceStatus.WAIT.value)
        self.assertEqual(resources2[0].instance_remark, 'tes的歌曲')
        self.assertEqual(order2.trading_status, order2.TradingStatus.OPENING.value)
        self.assertEqual(order2.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order2.resource_type, ResourceType.VM_SNAPSHOT.value)
        self.assertEqual(order2.owner_type, OwnerType.USER.value)
        self.assertEqual(order2.user_id, self.user.id)
        self.assertEqual(order2.period, 2)
        self.assertEqual(order2.period_unit, Order.PeriodUnit.MONTH.value)

        original_price = self.price.vm_disk_snap * 200 * 24 * 30 * 2
        trade_price = original_price * Decimal.from_float(self.price.prepaid_discount / 100)
        self.assertEqual(order2.total_amount, quantize_10_2(original_price))
        self.assertEqual(order2.payable_amount, quantize_10_2(trade_price))
        cfg = ServerSnapshotConfig.from_dict(order2.instance_config)
        self.assertEqual(cfg.server_id, server1.id)
        self.assertEqual(cfg.systemdisk_size, 200)
        self.assertEqual(cfg.snapshot_name, 'snapshot_name1')
        self.assertEqual(cfg.snapshot_desc, 'tes的歌曲')

        # vo server
        self.assertEqual(Order.objects.count(), 2)
        response = self.client.post(base_url, data={
            'server_id': vo_server.id,
            'snapshot_name': 'snapshot_name3',
            'description': 'description3',
            'period': 64,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # user2
        self.client.logout()
        self.client.force_login(self.user2)

        response = self.client.post(base_url, data={
            'server_id': vo_server.id,
            'snapshot_name': 'snapshot_name3',
            'description': 'description3',
            'period': 64,
            'period_unit': Order.PeriodUnit.DAY.value
        })
        self.assertEqual(response.status_code, 200)
        order3_id = response.data['order_id']
        self.assertEqual(Order.objects.count(), 3)
        order3, resources3 = OrderManager().get_order_detail(order_id=order3_id, user=self.user2)
        self.assertEqual(resources3[0].instance_status, resources3[0].InstanceStatus.WAIT.value)
        self.assertEqual(resources3[0].instance_remark, 'description3')
        self.assertEqual(order3.trading_status, order3.TradingStatus.OPENING.value)
        self.assertEqual(order3.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order3.resource_type, ResourceType.VM_SNAPSHOT.value)
        self.assertEqual(order3.owner_type, OwnerType.VO.value)
        self.assertEqual(order3.user_id, self.user2.id)
        self.assertEqual(order3.username, self.user2.username)
        self.assertEqual(order3.vo_id, self.vo.id)
        self.assertEqual(order3.period, 64)
        self.assertEqual(order3.period_unit, Order.PeriodUnit.DAY.value)

        original_price = self.price.vm_disk_snap * (128 * 24 * 64)
        trade_price = original_price * Decimal.from_float(self.price.prepaid_discount / 100)
        self.assertEqual(order3.total_amount, quantize_10_2(original_price))
        self.assertEqual(order3.payable_amount, quantize_10_2(trade_price))
        cfg = ServerSnapshotConfig.from_dict(order3.instance_config)
        self.assertEqual(cfg.server_id, vo_server.id)
        self.assertEqual(cfg.systemdisk_size, 128)
        self.assertEqual(cfg.snapshot_name, 'snapshot_name3')
        self.assertEqual(cfg.snapshot_desc, 'description3')

        response = self.client.post(base_url, data={
            'server_id': vo_server.id,
            'snapshot_name': 'snapshot_name4',
            'description': 'sfwefre隔热4',
            'period': 12,
            'period_unit': Order.PeriodUnit.MONTH.value
        })
        self.assertEqual(response.status_code, 200)
        order4_id = response.data['order_id']
        self.assertEqual(Order.objects.count(), 4)
        order4, resources4 = OrderManager().get_order_detail(order_id=order4_id, user=self.user2)
        self.assertEqual(resources4[0].instance_status, resources4[0].InstanceStatus.WAIT.value)
        self.assertEqual(resources4[0].instance_remark, 'sfwefre隔热4')
        self.assertEqual(order4.trading_status, order4.TradingStatus.OPENING.value)
        self.assertEqual(order4.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order4.resource_type, ResourceType.VM_SNAPSHOT.value)
        self.assertEqual(order4.owner_type, OwnerType.VO.value)
        self.assertEqual(order4.user_id, self.user2.id)
        self.assertEqual(order4.username, self.user2.username)
        self.assertEqual(order4.vo_id, self.vo.id)
        self.assertEqual(order4.period, 12)
        self.assertEqual(order4.period_unit, Order.PeriodUnit.MONTH.value)

        original_price = self.price.vm_disk_snap * (128 * 24 * 30 * 12)
        trade_price = original_price * Decimal.from_float(self.price.prepaid_discount / 100)
        self.assertEqual(order4.total_amount, quantize_10_2(original_price))
        self.assertEqual(order4.payable_amount, quantize_10_2(trade_price))
        cfg = ServerSnapshotConfig.from_dict(order4.instance_config)
        self.assertEqual(cfg.server_id, vo_server.id)
        self.assertEqual(cfg.systemdisk_size, 128)
        self.assertEqual(cfg.snapshot_name, 'snapshot_name4')
        self.assertEqual(cfg.snapshot_desc, 'sfwefre隔热4')

        order4.payable_amount = Decimal('0')
        order4.save(update_fields=['payable_amount'])
        pay_url = reverse('order-api:order-pay-order', kwargs={'id': order4_id})
        query = parse.urlencode(query={
            'payment_method': Order.PaymentMethod.BALANCE.value
        })
        response = self.client.post(f'{pay_url}?{query}')
        self.assertEqual(response.status_code, 200)

        order4.refresh_from_db()
        resources4[0].refresh_from_db()
        self.assertEqual(resources4[0].instance_status, resources4[0].InstanceStatus.FAILED.value)
        self.assertEqual(order4.trading_status, order4.TradingStatus.UNDELIVERED.value)
