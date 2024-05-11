from datetime import timedelta, datetime
from urllib import parse
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone

from apps.servers.models import ServiceConfig, ServerSnapshot
from apps.servers.tests import create_server_metadata
from utils.test import get_or_create_user, get_or_create_service, MyAPITransactionTestCase
from utils.model import PayType, OwnerType, ResourceType
from apps.vo.models import VirtualOrganization, VoMember
from apps.servers.managers import ServerSnapshotManager


class DiskOrderTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = get_or_create_user(username='user2')
        self.service = get_or_create_service()
        self.vo = VirtualOrganization(name='test vo', owner=self.user2)
        self.vo.save(force_insert=True)

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
        service2.org_data_center.users.add(self.user)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)

        # -------------- federal_admin ----------------
        self.service.users.remove(self.user)
        service2.users.remove(self.user)
        service2.org_data_center.users.remove(self.user)
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
