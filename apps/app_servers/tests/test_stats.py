from urllib import parse
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import (
    get_or_create_user, get_or_create_service,
    MyAPITransactionTestCase
)
from utils.model import PayType
from apps.app_vo.models import VirtualOrganization
from apps.app_servers.models import Server, Disk, ServiceConfig, ServerArchive
from . import create_server_metadata
from .test_disk import create_disk_metadata


class StastsTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()

    def test_res_stats(self):
        service2 = ServiceConfig(name='test2', name_en='test en 2')
        service2.save(force_insert=True)
        user2 = get_or_create_user(username='user2')
        vo1 = VirtualOrganization(name='test vo1', company='网络中心', description='unittest', owner=self.user)
        vo1.save(force_insert=True)

        server1 = create_server_metadata(
            service=self.service, user=self.user, ram=1, vcpus=2,
            default_user='', default_password='', creation_time=dj_timezone.now() - timedelta(days=100),
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )
        server2 = create_server_metadata(
            service=self.service, user=self.user, ram=2, vcpus=3,
            default_user='', default_password='', creation_time=dj_timezone.now() - timedelta(days=50),
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )
        server3 = create_server_metadata(
            service=service2, user=self.user, ram=3, vcpus=4,
            vo_id=vo1.id, classification=Server.Classification.VO.value,
            default_user='', default_password='', creation_time=dj_timezone.now(),
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )

        archieve_server1 = create_server_metadata(
            service=self.service, user=self.user, ram=4, vcpus=5,
            default_user='', default_password='', creation_time=dj_timezone.now() - timedelta(days=40),
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )
        archieve_server1.do_archive(archive_user=None)
        self.assertEqual(Server.objects.count(), 3)
        self.assertEqual(ServerArchive.objects.count(), 1)

        disk1 = create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=66, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=dj_timezone.now() - timedelta(days=60),
            expiration_time=dj_timezone.now() - timedelta(days=1),
            remarks='disk1 test', server_id=server1.id
        )
        disk2 = create_disk_metadata(
            service_id=service2.id, azone_id='2', disk_size=88, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=dj_timezone.now() - timedelta(days=120),
            expiration_time=dj_timezone.now() + timedelta(days=1),
            remarks='disk2 test', server_id=None, deleted=True
        )
        disk3_vo = create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=886, pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.VO.value, user_id=user2.id, vo_id=vo1.id,
            creation_time=dj_timezone.now(), expiration_time=None, remarks='vo disk3 test', server_id=server1.id
        )

        url = reverse('servers-api:stats-resources')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.user.set_fed_admin(is_fed=True)

        # all
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server', 'deleted_server', 'disk', 'deleted_disk'], response.data)
        self.assertEqual(response.data['server']['ram'], 1 + 2 + 3)
        self.assertEqual(response.data['server']['cpu'], 2 + 3 + 4)
        self.assertEqual(response.data['server']['count'], 3)
        self.assertEqual(response.data['deleted_server']['ram'], 4)
        self.assertEqual(response.data['deleted_server']['cpu'], 5)
        self.assertEqual(response.data['deleted_server']['count'], 1)
        self.assertEqual(response.data['disk']['count'], 2)
        self.assertEqual(response.data['disk']['size'], 66 + 886)
        self.assertEqual(response.data['deleted_disk']['count'], 1)
        self.assertEqual(response.data['deleted_disk']['size'], 88)

        # service
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server', 'deleted_server', 'disk', 'deleted_disk'], response.data)
        self.assertEqual(response.data['server']['ram'], 1 + 2)
        self.assertEqual(response.data['server']['cpu'], 2 + 3)
        self.assertEqual(response.data['server']['count'], 2)
        self.assertEqual(response.data['deleted_server']['ram'], 4)
        self.assertEqual(response.data['deleted_server']['cpu'], 5)
        self.assertEqual(response.data['deleted_server']['count'], 1)
        self.assertEqual(response.data['disk']['count'], 2)
        self.assertEqual(response.data['disk']['size'], 66 + 886)
        self.assertEqual(response.data['deleted_disk']['count'], 0)
        self.assertEqual(response.data['deleted_disk']['size'], 0)

        # time_start
        days_90_ago = dj_timezone.now() - timedelta(days=90)
        query = parse.urlencode(query={'time_start': days_90_ago.isoformat()})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server', 'deleted_server', 'disk', 'deleted_disk'], response.data)
        self.assertEqual(response.data['server']['ram'], 2 + 3)
        self.assertEqual(response.data['server']['cpu'], 3 + 4)
        self.assertEqual(response.data['server']['count'], 2)
        self.assertEqual(response.data['deleted_server']['ram'], 4)
        self.assertEqual(response.data['deleted_server']['cpu'], 5)
        self.assertEqual(response.data['deleted_server']['count'], 1)
        self.assertEqual(response.data['disk']['count'], 2)
        self.assertEqual(response.data['disk']['size'], 66 + 886)
        self.assertEqual(response.data['deleted_disk']['count'], 0)
        self.assertEqual(response.data['deleted_disk']['size'], 0)

        # time_end
        days_12_ago = dj_timezone.now() - timedelta(days=12)
        query = parse.urlencode(query={'time_end': days_12_ago.isoformat()})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server', 'deleted_server', 'disk', 'deleted_disk'], response.data)
        self.assertEqual(response.data['server']['ram'], 1 + 2)
        self.assertEqual(response.data['server']['cpu'], 2 + 3)
        self.assertEqual(response.data['server']['count'], 2)
        self.assertEqual(response.data['deleted_server']['ram'], 4)
        self.assertEqual(response.data['deleted_server']['cpu'], 5)
        self.assertEqual(response.data['deleted_server']['count'], 1)
        self.assertEqual(response.data['disk']['count'], 1)
        self.assertEqual(response.data['disk']['size'], 66)
        self.assertEqual(response.data['deleted_disk']['count'], 1)
        self.assertEqual(response.data['deleted_disk']['size'], 88)

        # time_start and time_end
        days_12_ago = dj_timezone.now() - timedelta(days=12)
        query = parse.urlencode(query={'time_start': days_90_ago.isoformat(), 'time_end': days_12_ago.isoformat()})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server', 'deleted_server', 'disk', 'deleted_disk'], response.data)
        self.assertEqual(response.data['server']['ram'], 2)
        self.assertEqual(response.data['server']['cpu'], 3)
        self.assertEqual(response.data['server']['count'], 1)
        self.assertEqual(response.data['deleted_server']['ram'], 4)
        self.assertEqual(response.data['deleted_server']['cpu'], 5)
        self.assertEqual(response.data['deleted_server']['count'], 1)
        self.assertEqual(response.data['disk']['count'], 1)
        self.assertEqual(response.data['disk']['size'], 66)
        self.assertEqual(response.data['deleted_disk']['count'], 0)
        self.assertEqual(response.data['deleted_disk']['size'], 0)
