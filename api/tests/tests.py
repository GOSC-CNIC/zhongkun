import hashlib
import collections
import io
import random
from datetime import datetime, timedelta
from string import printable
from urllib import parse
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from utils.model import PayType, OwnerType
from servers.models import Flavor, Server, Disk
from service.models import (
    ApplyOrganization, DataCenter, ApplyVmService, ServiceConfig
)
from utils.test import get_or_create_user, get_or_create_service, get_or_create_center
from adapters import outputs
from vo.models import VirtualOrganization, VoMember
from bill.managers.payment import PaymentManager
from order.managers import OrderManager
from order.models import Order, ResourceType
from order.managers.instance_configs import ServerConfig
from servers.models import ResourceActionLog
from . import MyAPITestCase, set_auth_header


def random_string(length: int = 10):
    return random.choices(printable, k=length)


def random_bytes_io(mb_num: int):
    bio = io.BytesIO()
    for i in range(1024):  # MB
        s = ''.join(random_string(mb_num))
        b = s.encode() * 1024  # KB
        bio.write(b)

    bio.seek(0)
    return bio


def calculate_md5(file):
    if hasattr(file, 'seek'):
        file.seek(0)

    md5obj = hashlib.md5()
    if isinstance(file, collections.Iterable):
        for data in file:
            md5obj.update(data)
    else:
        for data in chunks(file):
            md5obj.update(data)

    _hash = md5obj.hexdigest()
    return _hash


def chunks(f, chunk_size=2 * 2 ** 20):
    """
    Read the file and yield chunks of ``chunk_size`` bytes (defaults to
    ``File.DEFAULT_CHUNK_SIZE``).
    """
    try:
        f.seek(0)
    except AttributeError:
        pass

    while True:
        data = f.read(chunk_size)
        if not data:
            break
        yield data


def create_server_metadata(
        service, user, vo_id=None,
        default_user: str = 'root', default_password: str = 'password',
        classification=Server.Classification.PERSONAL, ipv4: str = '',
        expiration_time=None, public_ip: bool = False, remarks: str = '',
        pay_type: str = PayType.POSTPAID.value, vcpus: int = 2, ram: int = 1024,
        disk_size: int = 100, azone_id: str = ''
):
    server = Server(service=service,
                    instance_id='test',
                    remarks=remarks,
                    user=user,
                    vcpus=vcpus,
                    ram=ram,
                    disk_size=disk_size,
                    ipv4=ipv4 if ipv4 else '127.0.0.1',
                    image='test-image',
                    task_status=Server.TASK_CREATED_OK,
                    public_ip=public_ip,
                    classification=classification,
                    vo_id=vo_id,
                    image_id='',
                    image_desc='image desc',
                    default_user=default_user,
                    pay_type=pay_type,
                    creation_time=timezone.now(),
                    azone_id=azone_id
                    )
    server.raw_default_password = default_password
    if expiration_time:
        server.expiration_time = expiration_time

    server.save()
    return server


class ServersTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.default_user = 'root'
        self.default_password = 'password'
        self.miss_server = create_server_metadata(
            service=self.service, user=self.user, ram=1,
            default_user=self.default_user, default_password=self.default_password,
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )
        vo_data = {
            'name': 'test vo', 'company': '网络中心', 'description': 'unittest'
        }
        response = VoTests.create_vo_response(client=self.client, name=vo_data['name'],
                                              company=vo_data['company'], description=vo_data['description'])
        self.vo_id = response.data['id']
        self.vo_server = create_server_metadata(
            service=self.service, user=self.user, vo_id=self.vo_id, ram=2,
            classification=Server.Classification.VO, default_user=self.default_user,
            default_password=self.default_password,
            ipv4='127.0.0.12', remarks='test'
        )

    @staticmethod
    def server_detail_response(client, server_id, querys: dict = None):
        url = reverse('api:servers-detail', kwargs={'id': server_id})
        if querys:
            query = parse.urlencode(query=querys)
            url = f'{url}?{query}'

        response = client.get(url)
        if response.status_code == 500:
            print(response.data)

        return response

    def test_server_remark(self):
        url = reverse('api:servers-server-remark', kwargs={'id': self.miss_server.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, 400)

        url = reverse('api:servers-server-remark', kwargs={'id': '00'})
        query = parse.urlencode(query={'remark': 'ss'})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 404)

        remark = 'test-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.miss_server.refresh_from_db()
        self.assertEqual(remark, self.miss_server.remarks)

        # vo server when vo owner
        remark = 'test-vo-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.vo_server.refresh_from_db()
        self.assertEqual(remark, self.vo_server.remarks)

    def test_server_status(self):
        url = reverse('api:servers-server_status', kwargs={'id': self.miss_server.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        # vo server
        url = reverse('api:servers-server_status', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        url = reverse('api:servers-server_status', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertKeysIn(['code', 'message'], response.data)
        self.assertEqual(response.data['code'], 'NotFound')

        # ----------------admin get server status test -----------------------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)

        # test when not admin
        url = reverse('api:servers-server_status', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(admin_user)

        # test when service admin
        self.service.users.add(admin_user)
        url = reverse('api:servers-server_status', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        # test when federal admin
        self.service.users.remove(admin_user)
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        url = reverse('api:servers-server_status', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

    def test_server_detail(self):
        response = self.server_detail_response(client=self.client, server_id='motfound')
        self.assertEqual(response.status_code, 404)
        self.assertKeysIn(['code', 'message'], response.data)
        self.assertEqual(response.data['code'], 'NotFound')

        response = self.server_detail_response(client=self.client, server_id=self.miss_server.id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "endpoint_url", "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password", "pay_type",
                           "attached_disks"], response.data['server'])
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['server']['service'])
        self.assert_is_subdict_of(sub={
            "default_user": self.default_user, "default_password": self.default_password
        }, d=response.data['server'])
        self.assertIsInstance(response.data['server']['attached_disks'], list)
        self.assertEqual(len(response.data['server']['attached_disks']), 0)

        # ----------------admin get server detail test -----------------------
        from .test_disk import create_disk_metadata
        create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=6, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), server_id=self.miss_server.id
        )
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)

        # test when not admin
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(admin_user)

        # test when service admin
        self.service.users.add(admin_user)
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "endpoint_url", "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password", "pay_type",
                           "attached_disks"], response.data['server'])
        self.assert_is_subdict_of(sub={
            "default_user": self.default_user, "default_password": self.default_password
        }, d=response.data['server'])
        self.assertIsInstance(response.data['server']['attached_disks'], list)
        self.assertEqual(len(response.data['server']['attached_disks']), 1)
        self.assertKeysIn(["id", "size", "creation_time", "remarks", "expiration_time", "mountpoint",
                           "attached_time", "detached_time", "pay_type"], response.data['server']['attached_disks'][0])

        # test when federal admin
        self.service.users.remove(admin_user)

        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "endpoint_url", "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password", "pay_type"
                           ], response.data['server'])

    def test_server_list(self):
        vo_server = self.vo_server
        vo_id = self.vo_id
        # list user servers
        url = reverse('api:servers-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ram_gib", "ipv4",
                           "public_ip", "image", "creation_time",
                           "remarks", "endpoint_url", "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password",
                           "lock", "pay_type"], response.data['servers'][0])
        self.assertEqual(response.data['servers'][0]['ram_gib'], 1)
        self.assertEqual(response.data['servers'][0]['ram'], 1)
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['servers'][0]['service'])
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'service': {
                'id': self.miss_server.service.id, 'name': self.miss_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': self.miss_server.service.name_en
            },
            'id': self.miss_server.id, 'vo_id': None
        }, d=response.data['servers'][0])

        # param ip-contain
        url = reverse('api:servers-list')
        query = parse.urlencode({'ip-contain': self.miss_server.ipv4})
        url = f'{url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'id': self.miss_server.id, 'ipv4': self.miss_server.ipv4
        }, d=response.data['servers'][0])

        url = reverse('api:servers-list')
        query = parse.urlencode({'ip-contain': 'no-contain'})
        url = f'{url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        # query 'status' invalid
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'status': 's'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query status
        query_str = parse.urlencode(query={'status': 'expired'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        query_str = parse.urlencode(query={'status': 'prepaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query_str = parse.urlencode(query={'status': 'postpaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        # query "public"
        query_str = parse.urlencode(query={'public': 'tr'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query_str = parse.urlencode(query={'public': 'true'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)
        query_str = parse.urlencode(query={'public': 'false'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)

        # param "remark
        url = reverse('api:servers-list')
        query = parse.urlencode({'remark': 'miss'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'id': self.miss_server.id, 'ipv4': self.miss_server.ipv4
        }, d=response.data['servers'][0])
        query = parse.urlencode({'remark': 'ssmiss'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # query 'user-id' only as-admin
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'user-id': 'c'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # query 'username' only as-admin
        query_str = parse.urlencode(query={'username': 'c'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # query 'vo-id' only as-admin
        query_str = parse.urlencode(query={'vo-id': 'c'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # query 'vo-name' only as-admin
        query_str = parse.urlencode(query={'vo-name': 'c'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # query 'exclude-vo' only as-admin
        query_str = parse.urlencode(query={'exclude-vo': None})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # list vo servers
        url = reverse('api:servers-list-vo-servers', kwargs={'vo_id': self.vo_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['count'], 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time",
                           "remarks", "endpoint_url", "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password",
                           "lock", "pay_type"], response.data['servers'][0])
        self.assertEqual(response.data['servers'][0]['ram_gib'], 2)
        self.assertEqual(response.data['servers'][0]['ram'], 2)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': vo_server.service.id, 'name': vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': vo_server.service.name_en
            },
            'id': vo_server.id, 'vo_id': vo_id
        }, d=response.data['servers'][0])

        # query 'expired' invalid
        url = reverse('api:servers-list-vo-servers', kwargs={'vo_id': self.vo_id})
        query_str = parse.urlencode(query={'expired': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query expired
        query_str = parse.urlencode(query={'expired': 'true'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        # query not expired
        query_str = parse.urlencode(query={'expired': 'false'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(self.vo_server.ipv4, response.data['servers'][0]['ipv4'])

        # server vo detail
        response = self.server_detail_response(
            client=self.client, server_id=self.vo_server.id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time", "remarks",
                           "endpoint_url", "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password",
                           "lock", "pay_type"], response.data['server'])
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': vo_server.service.id, 'name': vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': vo_server.service.name_en
            },
            'id': vo_server.id, 'vo_id': vo_id
        }, d=response.data['server'])

        # ----------------admin list servers test -----------------------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)
        service66 = ServiceConfig(
            name='test66', name_en='test66_en', org_data_center_id=None,
            endpoint_url='',
            username='',
            service_type=ServiceConfig.ServiceType.EVCLOUD,
            region_id='',
        )
        service66.save()
        admin_server66 = create_server_metadata(
            service=service66, user=admin_user, remarks='admin test',
            default_user=self.default_user, default_password=self.default_password,
            ipv4='159.226.235.66', expiration_time=timezone.now(), public_ip=True
        )

        self.client.logout()
        self.client.force_login(admin_user)

        # list server when not admin user
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # -------------list server when service admin---------------
        self.service.users.add(admin_user)

        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 2)

        # query 'status' invalid
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'dd'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query status
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'expired'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        query_str = parse.urlencode(query={'as-admin': '', 'status': 'prepaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'postpaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.vo_server.id)

        # query "public"
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'tr'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'true'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'false'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # param "remark
        url = reverse('api:servers-list')
        query = parse.urlencode(query={'as-admin': '', 'remark': 'miss'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query = parse.urlencode(query={'as-admin': '', 'remark': 'admin'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        query = parse.urlencode(query={'as-admin': '', 'remark': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

        # list server when service admin bu query parameter 'service_id'
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # list server when service admin bu query parameter 'service_id' and 'user-id'
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id, 'user-id': admin_user.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id, 'user-id': self.user.id,
                                           'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time",
                           "remarks", "endpoint_url", "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password",
                           "lock", "pay_type"], response.data['servers'][0])
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'service': {
                'id': self.miss_server.service.id, 'name': self.miss_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': self.miss_server.service.name_en
            },
            'id': self.miss_server.id, 'vo_id': None
        }, d=response.data['servers'][0])

        # list server when service admin bu query parameter 'service_id' and 'vo-id'
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id, 'vo-id': self.vo_id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': vo_server.service.id, 'name': vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': vo_server.service.name_en
            },
            'id': vo_server.id, 'vo_id': vo_id
        }, d=response.data['servers'][0])

        # list server when service admin by query parameter 'user-id' and 'username'
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'user-id': self.user.id, 'username': self.user.username})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # list server when service admin by query parameter 'vo-id' and 'vo-name'
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'vo-id': self.vo_id, 'vo-name': 'dd'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # list server when service admin by query parameter 'vo-id' and 'exclude-vo'
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'vo-id': self.vo_id, 'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # list server when service admin by query parameter 'vo-name' and 'exclude-vo'
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'exclude-vo': '', 'vo-name': 'dd'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # org data center admin
        self.service.users.remove(admin_user)
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 0)

        self.service.org_data_center.users.add(admin_user)
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 2)

        # -------------list server when federal admin---------------
        admin_user.set_federal_admin()
        url = reverse('api:servers-list')
        query_str = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['servers']), 3)

        # query "exclude-vo"
        query_str = parse.urlencode(query={'as-admin': '', 'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # query "username"
        query_str = parse.urlencode(query={'as-admin': '', 'username': self.user.username})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # query "username" and "exclude-vo"
        query_str = parse.urlencode(query={'as-admin': '', 'username': self.user.username, 'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)

        # query "user-id"
        query_str = parse.urlencode(query={'as-admin': '', 'user-id': self.user.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # query "user-id" and "exclude-vo"
        query_str = parse.urlencode(query={'as-admin': '', 'user-id': self.user.id, 'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)

        # query "user-id"
        query_str = parse.urlencode(query={'as-admin': '', 'user-id': admin_user.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], admin_server66.id)

        # query "vo-id"
        query_str = parse.urlencode(query={'as-admin': '', 'vo-id': self.vo_id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.vo_server.id)

        # query "vo-id" and "user-id"
        query_str = parse.urlencode(query={'as-admin': '', 'vo-id': self.vo_id, 'user-id': self.user.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.vo_server.id)

        # query "vo-name"
        query_str = parse.urlencode(query={'as-admin': '', 'vo-name': self.vo_server.vo.name})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.vo_server.id)

        # query 'status' invalid
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'ss'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query "status"
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'expired'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)
        # self.assertEqual(admin_server66.ipv4, response.data['servers'][0]['ipv4'])

        query_str = parse.urlencode(query={'as-admin': '', 'status': 'prepaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'postpaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # query "public"
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'tr'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'true'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], admin_server66.id)
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'false'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # param "remark
        url = reverse('api:servers-list')
        query = parse.urlencode(query={'as-admin': '', 'remark': 'miss'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query = parse.urlencode(query={'as-admin': '', 'remark': 'admin'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['servers'][0]['id'], admin_server66.id)
        query = parse.urlencode(query={'as-admin': '', 'remark': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)

        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id, 'vo-id': self.vo_id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)

        query_str = parse.urlencode(query={'as-admin': '', 'ip-contain': '0.0.1'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        query_str = parse.urlencode(query={'as-admin': '', 'ip-contain': admin_server66.ipv4})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(admin_server66.ipv4, response.data['servers'][0]['ipv4'])

    def test_server_action(self):
        url = reverse('api:servers-server-action', kwargs={'id': 'motfound'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(url, data={'action': 'test'})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # ----------------admin action server test -----------------------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)
        self.client.logout()
        self.client.force_login(admin_user)

        # test when not admin
        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # test when service admin
        self.service.users.add(admin_user)
        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # test when federal admin
        self.service.users.remove(admin_user)
        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # ------ 过期停服停机挂起的云主机测试 -----------
        self.client.logout()
        self.client.force_login(user=self.user)
        user_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password,
            ipv4='127.0.0.1'
        )
        user_server.expiration_time = timezone.now()
        user_server.situation = Server.Situation.EXPIRED.value
        user_server.save(update_fields=['situation', 'expiration_time'])
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.EXPIRED.value)

        url = reverse('api:servers-server-action', kwargs={'id': user_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ExpiredSuspending', response=response)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.EXPIRED.value)

        # 是否欠费查询时，no pay_app_service_id
        user_server.expiration_time = timezone.now() + timedelta(days=1)
        user_server.save(update_fields=['expiration_time'])
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.NORMAL.value)

        # 未管控，按量计费云主机 欠费也不允许开机
        self.user.userpointaccount.balance = Decimal('-0.01')
        self.user.userpointaccount.save(update_fields=['balance'])
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ArrearageSuspending', response=response)

        # 未管控，预付费云主机 欠费也不允许开机
        user_server.expiration_time = timezone.now() - timedelta(days=1)
        user_server.pay_type = PayType.PREPAID.value
        user_server.save(update_fields=['expiration_time', 'pay_type'])
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ExpiredSuspending', response=response)

        # ------ 欠费停服停机挂起的云主机测试 -----------
        service = self.vo_server.service
        service.pay_app_service_id = 'test'
        service.save(update_fields=['pay_app_service_id'])

        self.vo_server.situation = Server.Situation.ARREARAGE.value
        self.vo_server.save(update_fields=['situation'])
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.ARREARAGE.value)

        url = reverse('api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.NORMAL.value)

        vopointaccount = self.vo_server.vo.vopointaccount
        vopointaccount.balance = Decimal('-1')
        vopointaccount.save(update_fields=['balance'])
        self.vo_server.situation = Server.Situation.ARREARAGE.value
        self.vo_server.save(update_fields=['situation'])
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.ARREARAGE.value)

        url = reverse('api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ArrearageSuspending', response=response)
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.ARREARAGE.value)

        # 未管控时，按量计费云主机 欠费 不允许开机
        self.vo_server.situation = Server.Situation.NORMAL.value
        self.vo_server.save(update_fields=['situation'])
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.NORMAL.value)
        url = reverse('api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ArrearageSuspending', response=response)

    def test_vo_server_permission(self):
        member_user = get_or_create_user(username='vo-member')
        self.client.logout()
        self.client.force_login(member_user)

        # -------no permission------
        # vo server remark
        remark = 'test-vo-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # list vo servers
        url = reverse('api:servers-list-vo-servers', kwargs={'vo_id': self.vo_id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # action server
        url = reverse('api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo server status
        url = reverse('api:servers-server_status', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # server vo detail
        response = self.server_detail_response(
            client=self.client, server_id=self.vo_server.id)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # server vnc
        url = reverse('api:servers-server-vnc', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # ----- add vo member ------
        self.client.logout()
        self.client.force_login(self.user)
        response = VoTests.add_members_response(client=self.client, vo_id=self.vo_id, usernames=[member_user.username])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['success']), 1)
        self.client.logout()
        self.client.force_login(member_user)

        # -------has permission-----

        # list vo servers
        url = reverse('api:servers-list-vo-servers', kwargs={'vo_id': self.vo_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['count'], 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "endpoint_url", "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password",
                           "lock", "pay_type"], response.data['servers'][0])
        vo_server = self.vo_server
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': vo_server.service.id, 'name': vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': vo_server.service.name_en
            },
            'id': vo_server.id, 'vo_id': self.vo_id
        }, d=response.data['servers'][0])
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['servers'][0]['service'])

        # action server
        url = reverse('api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # vo server status
        url = reverse('api:servers-server_status', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        # server vo detail
        response = self.server_detail_response(client=self.client, server_id=self.vo_server.id)
        self.assertEqual(response.status_code, 200)

        # server vnc
        url = reverse('api:servers-server-vnc', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # delete vo server need vo leader role
        url = reverse('api:servers-detail', kwargs={'id': self.vo_server.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # action server
        url = reverse('api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'delete'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo server remark when not vo member leader
        remark = 'test-vo-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo server remark when vo member leader
        vo_member = VoMember.objects.filter(vo_id=self.vo_id, user_id=member_user.id).first()
        vo_member.role = VoMember.Role.LEADER
        vo_member.save(update_fields=['role'])

        remark = 'test-vo-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.vo_server.refresh_from_db()
        self.assertEqual(remark, self.vo_server.remarks)

    def test_delete_list_archive(self):
        self.client.logout()
        self.client.force_login(self.user)
        url = reverse('api:servers-detail', kwargs={'id': 'motfound'})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        log_count = ResourceActionLog.objects.count()
        self.assertEqual(log_count, 0)
        url = reverse('api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        log_count = ResourceActionLog.objects.count()
        self.assertEqual(log_count, 1)
        log: ResourceActionLog = ResourceActionLog.objects.order_by('-action_time').first()
        self.assertEqual(log.action_flag, ResourceActionLog.ActionFlag.DELETION.value)
        self.assertEqual(log.resource_id, self.miss_server.id)
        self.assertEqual(log.resource_type, ResourceActionLog.ResourceType.SERVER.value)
        self.assertEqual(log.owner_type, OwnerType.USER.value)

        url = reverse('api:servers-detail', kwargs={'id': self.vo_server.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        log_count = ResourceActionLog.objects.count()
        self.assertEqual(log_count, 2)
        log: ResourceActionLog = ResourceActionLog.objects.order_by('-action_time').first()
        self.assertEqual(log.action_flag, ResourceActionLog.ActionFlag.DELETION.value)
        self.assertEqual(log.resource_id, self.vo_server.id)
        self.assertEqual(log.resource_type, ResourceActionLog.ResourceType.SERVER.value)
        self.assertEqual(log.owner_type, OwnerType.VO.value)

        # list user server archives
        url = reverse('api:server-archive-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        obj = response.data['results'][0]
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time",
                           "remarks", "service",
                           "center_quota", "deleted_time", "classification", "vo_id",
                           "pay_type", "server_id"], obj)
        self.assertEqual(obj['ram_gib'], 1)
        self.assertEqual(obj['ram'], 1)
        self.assertKeysIn(["id", "name", "name_en", "service_type"], obj['service'])
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'service': {
                'id': self.miss_server.service.id, 'name': self.miss_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': self.miss_server.service.name_en
            },
            'vo_id': None
        }, d=obj)
        UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
        self.assertEqual(datetime.strptime(obj['creation_time'], UTC_FORMAT).timestamp(),
                         self.miss_server.creation_time.timestamp())

        # list vo server archives
        url = reverse('api:server-archive-list-vo-archives', kwargs={'vo_id': self.vo_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time",
                           "remarks", "service",
                           "center_quota", "deleted_time", "classification", "vo_id",
                           "pay_type", "server_id"], response.data["results"][0])
        self.assertEqual(response.data['results'][0]['ram_gib'], 2)
        self.assertEqual(response.data['results'][0]['ram'], 2)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': self.vo_server.service.id, 'name': self.vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': self.vo_server.service.name_en
            },
            'vo_id': self.vo_id
        }, d=response.data['results'][0])

        # ----------------admin delete server test -----------------------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)

        delete_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password)

        self.client.logout()
        self.client.force_login(admin_user)

        # test when not admin
        base_url = reverse('api:servers-detail', kwargs={'id': delete_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        delete_url = f'{base_url}?{query}'
        response = self.client.delete(delete_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # test when service admin
        self.service.users.add(admin_user)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)

        # test when federal admin
        self.service.users.remove(admin_user)
        delete_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password)

        base_url = reverse('api:servers-detail', kwargs={'id': delete_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        delete_url = f'{base_url}?{query}'
        response = self.client.delete(delete_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)

    def test_server_lock(self):
        # server remark
        remark = 'test-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.miss_server.refresh_from_db()
        self.assertEqual(remark, self.miss_server.remarks)

        # server action
        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # ---- lock server delete ------
        url = reverse('api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.DELETE})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.DELETE)

        # server remark
        remark = 'test-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.miss_server.refresh_from_db()
        self.assertEqual(remark, self.miss_server.remarks)

        # server action
        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        url = reverse('api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # ---- lock server all operation ------
        url = reverse('api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.OPERATION})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.OPERATION)

        # server remark
        remark = 'test-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # server action
        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # server delete
        url = reverse('api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # server action delete
        url = reverse('api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'delete'})
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # server rebuild
        url = reverse('api:servers-rebuild', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'image_id': 'aaa'})
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # ---- lock server free ------
        url = reverse('api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.FREE})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.FREE)

        # ----as admin------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)

        self.client.logout()
        self.client.force_login(admin_user)

        url = reverse('api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.OPERATION.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # service admin
        self.service.users.add(admin_user)
        query = parse.urlencode(query={'lock': Server.Lock.OPERATION.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.OPERATION.value)

        url = reverse('api:servers-server-lock', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.FREE.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.FREE.value)

        # federal admin
        self.service.users.remove(admin_user)
        url = reverse('api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.FREE.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        query = parse.urlencode(query={'lock': Server.Lock.FREE.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.FREE.value)

        # server delete
        self.client.logout()
        self.client.force_login(self.user)
        url = reverse('api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        # server action delete
        url = reverse('api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'delete'})
        self.assertEqual(response.status_code, 200)

    def test_server_rebuild(self):
        miss_server = self.miss_server
        url = reverse('api:servers-rebuild', kwargs={'id': miss_server.id})

        # no body
        response = self.client.post(url, data={})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        miss_server.task_status = miss_server.TASK_IN_CREATING
        miss_server.save(update_fields=['task_status'])
        response = self.client.post(url, data={'image_id': 'aaa'})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        miss_server.task_status = miss_server.TASK_CREATED_OK
        miss_server.save(update_fields=['task_status'])
        response = self.client.post(url, data={'image_id': 'test'})
        self.assertEqual(response.status_code, 500)

        # ------ 过期停服停机挂起的云主机测试 -----------
        self.client.logout()
        self.client.force_login(user=self.user)
        user_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password,
            ipv4='127.0.0.1'
        )
        user_server.expiration_time = timezone.now()
        user_server.situation = Server.Situation.EXPIRED.value
        user_server.save(update_fields=['situation', 'expiration_time'])
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.EXPIRED.value)

        url = reverse('api:servers-rebuild', kwargs={'id': user_server.id})
        response = self.client.post(url, data={'image_id': 'test'})
        self.assertErrorResponse(status_code=409, code='ExpiredSuspending', response=response)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.EXPIRED.value)

        user_server.expiration_time = timezone.now() + timedelta(days=1)
        user_server.save(update_fields=['expiration_time'])
        response = self.client.post(url, data={'image_id': 'test'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.NORMAL.value)


class ServiceTests(MyAPITestCase):
    def setUp(self):
        self.user = None
        set_auth_header(self)
        self.service = get_or_create_service()

    def test_list_service(self):
        service2 = ServiceConfig(name='service2', name_en='service2 en')
        service2.save(force_insert=True)

        url = reverse('api:service-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertKeysIn(["id", "name", "name_en", "service_type", "cloud_type", "add_time", "sort_weight",
                           "need_vpn", "status", "org_data_center", 'longitude', 'latitude', 'pay_app_service_id',
                           'disk_available'], response.data["results"][0])
        self.assertEqual(len(response.data["results"]), 2)
        map_ = {s['id']: s for s in response.data["results"]}
        r_service1 = map_[self.service.id]
        r_service2 = map_[service2.id]
        self.assertKeysIn([
            "id", "name", "name_en", "sort_weight", "organization"], r_service1['org_data_center'])
        self.assertKeysIn(["id", "name", "name_en"], r_service1['org_data_center']['organization'])
        self.assertIsInstance(r_service1['status'], str)
        self.assertEqual(r_service1['status'], ServiceConfig.Status.ENABLE)
        self.assertIs(r_service1['disk_available'], False)
        self.assertIsNone(r_service2['org_data_center'])

        url = reverse('api:service-list')
        query = parse.urlencode(query={'center_id': self.service.org_data_center_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        url = reverse('api:service-list')
        query = parse.urlencode(query={'center_id': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # query "org_id"
        query = parse.urlencode(query={'org_id': self.service.org_data_center.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        query = parse.urlencode(query={'org_id': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # invalid param 'status'
        url = reverse('api:service-list')
        query = parse.urlencode(query={'status': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidStatus', response=response)

        # param 'status'
        url = reverse('api:service-list')
        query = parse.urlencode(query={'status': 'enable'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        service2.status = ServiceConfig.Status.DELETED.value
        service2.save(update_fields=['status'])
        query = parse.urlencode(query={'status': ServiceConfig.Status.ENABLE.value})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data['results'][0]['id'], self.service.id)
        self.assertEqual(response.data['results'][0]['status'], ServiceConfig.Status.ENABLE.value)

        query = parse.urlencode(query={'status': ServiceConfig.Status.DISABLE.value})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        query = parse.urlencode(query={'status': ServiceConfig.Status.DELETED.value})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data['results'][0]['id'], service2.id)
        self.assertEqual(response.data['results'][0]['status'], ServiceConfig.Status.DELETED.value)

    def test_admin_list(self):
        url = reverse('api:service-admin-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data['count'], 0)

        self.service.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertKeysIn(["id", "name", "name_en", "service_type", "cloud_type", "add_time", "sort_weight",
                           "need_vpn", "status", "org_data_center", 'longitude', 'latitude', 'pay_app_service_id',
                           'disk_available'], response.data["results"][0])
        self.assertKeysIn([
            "id", "name", "name_en", "sort_weight", "organization"], response.data["results"][0]['org_data_center'])
        self.assertKeysIn(["id", "name", "name_en"], response.data["results"][0]['org_data_center']['organization'])
        self.assertIsInstance(response.data["results"][0]['status'], str)

        # 数据中心管理员
        self.service.users.remove(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        self.service.org_data_center.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def service_quota_get_update(self, url):
        # get
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["private_ip_total", "public_ip_total", "vcpu_total", "ram_total",
                           'disk_size_total', 'private_ip_used', 'public_ip_used',
                           'vcpu_used', 'ram_used', 'disk_size_used', 'creation_time',
                           'enable'], response.data)
        self.assert_is_subdict_of(sub={
            'private_ip_total': 0, 'public_ip_total': 0, 'vcpu_total': 0, 'ram_total': 0,
            'disk_size_total': 0, 'private_ip_used': 0, 'public_ip_used': 0, 'vcpu_used': 0,
            'ram_used': 0, 'disk_size_used': 0, 'enable': True
        }, d=response.data)

        # update
        response = self.client.post(url, data={
            "private_ip_total": 1,
            "public_ip_total": 2,
            "vcpu_total": 3,
            "ram_total": 4,
            "disk_size_total": 5
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["private_ip_total", "public_ip_total", "vcpu_total", "ram_total",
                           'disk_size_total', 'private_ip_used', 'public_ip_used',
                           'vcpu_used', 'ram_used', 'disk_size_used', 'creation_time',
                           'enable'], response.data)
        self.assert_is_subdict_of(sub={
            'private_ip_total': 1, 'public_ip_total': 2, 'vcpu_total': 3, 'ram_total': 4,
            'disk_size_total': 5, 'private_ip_used': 0, 'public_ip_used': 0, 'vcpu_used': 0,
            'ram_used': 0, 'disk_size_used': 0, 'enable': True
        }, d=response.data)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assert_is_subdict_of(sub={
            'private_ip_total': 1, 'public_ip_total': 2, 'vcpu_total': 3, 'ram_total': 4,
            'disk_size_total': 5, 'private_ip_used': 0, 'public_ip_used': 0, 'vcpu_used': 0,
            'ram_used': 0, 'disk_size_used': 0, 'enable': True
        }, d=response.data)

    def test_private_quota(self):
        url = reverse('api:service-private-quota', kwargs={'id': self.service.id})
        self.service_quota_get_update(url=url)

    def test_share_quota(self):
        url = reverse('api:service-share-quota', kwargs={'id': self.service.id})
        self.service_quota_get_update(url=url)


class ImageTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()

    def test_list_image(self):
        url = reverse('api:images-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        url += f'?service_id={self.service.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertKeysIn(["id", "name", "system", "system_type",
                           "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb", "min_ram_mb"
                           ], response.data[0])

        # image detail
        image_id = response.data[0]['id']
        url = reverse('api:images-detail', kwargs={'id': image_id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        url = reverse('api:images-detail', kwargs={'id': image_id})
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "name", "system_type", "release", "version", "architecture",
                           "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb", "min_ram_mb"
                           ], response.data)

    def test_list_image_paginate(self):
        url = reverse('api:images-paginate-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            "count", "page_num", "page_size", "results"
        ], response.data)
        self.assertIsInstance(response.data['results'], list)
        self.assertKeysIn([
            "id", "name", "release", "version", "architecture", "system_type",
            "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb",
            "min_ram_mb"
        ], response.data['results'][0])

        default_get_length = len(response.data['results'])

        # query "page_size"
        page_size = max(default_get_length - 1, 1)
        url = reverse('api:images-paginate-list')
        query = parse.urlencode(query={
            'service_id': self.service.id, 'page_num': 1,
            'page_size': page_size
        })
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            "count", "page_num", "page_size", "results"
        ], response.data)
        self.assertIsInstance(response.data['results'], list)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertKeysIn([
            "id", "name", "release", "version", "architecture", "system_type",
            "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb",
            "min_ram_mb"
        ], response.data['results'][0])

        # image detail
        image_id = response.data['results'][0]['id']
        url = reverse('api:images-detail', kwargs={'id': image_id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        url = reverse('api:images-detail', kwargs={'id': image_id})
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            "id", "name", "release", "version", "architecture", "system_type",
            "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb",
            "min_ram_mb"
        ], response.data)


class NetworkTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()

    def test_list_network(self):
        base_url = reverse('api:networks-list')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        query = parse.urlencode({"azone_id": ''})
        url = f'{base_url}?{query}'
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        url = f'{base_url}?service_id={self.service.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        if response.data:
            self.assertKeysIn(["id", "name", "public", "segment"], response.data[0])

            network_id = response.data[0]['id']
            url = reverse('api:networks-detail', kwargs={'network_id': network_id})
            response = self.client.get(url)
            self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

            url += f'?service_id={self.service.id}'
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertKeysIn(["id", "name", "public", "segment"], response.data)
        else:
            network_id = '1'        # 不确定是否存在
            url = reverse('api:networks-detail', kwargs={'network_id': network_id})
            response = self.client.get(url)
            self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

            url += f'?service_id={self.service.id}'
            response = self.client.get(url)
            if response.status_code == 200:
                self.assertKeysIn(["id", "name", "public", "segment"], response.data)
            else:
                self.assertEqual(response.status_code, 500)


class RegistryTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.data_center = get_or_create_center()

    def test_list_registry(self):
        url = reverse('api:registry-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('registries', response.data)
        self.assertIsInstance(response.data['registries'], list)
        self.assertKeysIn(["id", "name", "endpoint_vms", "endpoint_object", "endpoint_compute", "sort_weight",
                           "endpoint_monitor", "creation_time", "status", "desc", 'longitude', 'latitude'],
                          response.data['registries'][0])


class MediaApiTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)

    def download_media_response(self, url_path: str):
        url = url_path  # reverse('api:media-detail', kwargs={'url_path': url_path})
        return self.client.get(url)

    @staticmethod
    def put_media_response(client, url_path: str, file):
        """200 ok"""
        url = reverse('api:media-detail', kwargs={'url_path': url_path})
        file_md5 = calculate_md5(file)
        headers = {'HTTP_Content_MD5': file_md5}
        file.seek(0)
        return client.put(url, data=file.read(),
                          content_type='application/octet-stream', **headers)

    def test_put_logo(self):
        prefix = 'logo'
        self.upload_download_test(prefix=prefix, is_return_md5_name=True)
        prefix = 'certification'
        self.upload_download_test(prefix=prefix, is_return_md5_name=True)
        prefix = 'test'
        self.upload_download_test(prefix=prefix, is_return_md5_name=False)

    def upload_download_test(self, prefix: str, is_return_md5_name: bool):
        file = random_bytes_io(mb_num=8)
        file_md5 = calculate_md5(file)
        ext = 'jpg'
        key = f'v2test.{ext}'
        response = self.put_media_response(self.client, url_path=f'{prefix}/{key}', file=file)
        self.assertEqual(response.status_code, 200)
        if is_return_md5_name:
            filename = f'{file_md5}.{ext}'
        else:
            filename = key

        response_url_path = reverse('api:media-detail', kwargs={'url_path': f'{prefix}/{filename}'})
        self.assertEqual(response.data['url_path'], response_url_path)

        url_path = response.data['url_path']
        response = self.download_media_response(url_path=url_path)
        self.assertEqual(response.status_code, 200)
        download_md5 = calculate_md5(response)
        self.assertEqual(download_md5, file_md5, msg='Compare the MD5 of upload file and download file')


class ApplyOrganizationTests(MyAPITestCase):
    apply_data = {
        "name": "中国科学院计算机信息网络中心",
        "name_en": "cnic",
        "abbreviation": "中科院网络中心",
        "independent_legal_person": True,
        "country": "中国",
        "city": "北京",
        "postal_code": "100083",
        "address": "北京市海淀区",
        "endpoint_vms": "https://vms.cstcloud.cn/",
        "endpoint_object": "",
        "endpoint_compute": "",
        "endpoint_monitor": "",
        "desc": "test",
        "logo_url": "/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg",
        "certification_url": "/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx",
        "longitude": -88,
        "latitude": 66
    }

    def setUp(self):
        self.user = None
        set_auth_header(self)
        self.federal_username = 'federal_admin'
        self.federal_password = 'federal_password'
        self.federal_admin = get_or_create_user(username=self.federal_username, password=self.federal_password)

    @staticmethod
    def create_apply_response(client, data: dict):
        url = reverse('api:apply-organization-list')
        return client.post(url, data=data)

    @staticmethod
    def action_apply_response(client, _id: str, action: str):
        url = reverse('api:apply-organization-action', kwargs={'id': _id, 'action': action})
        return client.post(url)

    def test_create_cancel_delete_apply(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'creation_time', 'status', 'user', 'deleted', 'name', "name_en", 'abbreviation',
            'independent_legal_person',
            'country', 'city', 'postal_code', 'address', 'endpoint_vms', 'endpoint_object',
            'endpoint_compute', 'endpoint_monitor', 'desc', 'logo_url', 'certification_url',
            "longitude", "latitude"
        ], container=response.data)
        self.assert_is_subdict_of(sub={
            'status': 'wait', 'deleted': False, 'name': '中国科学院计算机信息网络中心', "name_en": "cnic",
            'abbreviation': '中科院网络中心', 'independent_legal_person': True, 'country': '中国', 'city': '北京',
            'postal_code': '100083', 'address': '北京市海淀区', 'endpoint_vms': 'https://vms.cstcloud.cn/',
            'endpoint_object': '', 'endpoint_compute': '', 'endpoint_monitor': '', 'desc': 'test',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg',
            'certification_url': '/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx',
            "longitude": -88, "latitude": 66
        }, d=response.data)
        apply_id = response.data['id']

        apply_data['endpoint_object'] = 'test'
        url = reverse('api:apply-organization-list')
        response = self.client.post(url, data=apply_data)
        self.assertEqual(response.status_code, 400)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # cancel
        url = reverse('api:apply-organization-action', kwargs={'id': apply_id, 'action': 'cancel'})
        response = self.client.post(url, data=apply_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyOrganization.Status.CANCEL)

        # delete
        url = reverse('api:apply-organization-detail', kwargs={'id': apply_id})
        response = self.client.delete(url, data=apply_data)
        self.assertEqual(response.status_code, 204)

    def test_cancel_delete_pending_apply(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        # 联邦管理员权限
        self.client.logout()
        self.client.force_login(self.federal_admin)
        self.federal_admin.set_federal_admin()

        # cancel
        url = reverse('api:apply-organization-action', kwargs={'id': apply_id, 'action': 'cancel'})
        response = self.client.post(url, data=apply_data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # pending
        response = self.action_apply_response(client=self.client, _id=apply_id, action='pending')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyOrganization.Status.PENDING)

        # 普通用户
        self.client.logout()
        self.client.force_login(self.user)

        # cancel
        url = reverse('api:apply-organization-action', kwargs={'id': apply_id, 'action': 'cancel'})
        response = self.client.post(url, data=apply_data)
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # delete
        url = reverse('api:apply-organization-detail', kwargs={'id': apply_id})
        response = self.client.delete(url, data=apply_data)
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

    def test_create_pending_reject_apply(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        self.client.logout()
        self.client.force_login(self.federal_admin)
        response = self.action_apply_response(client=self.client, _id=apply_id, action='pending')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 联邦管理员权限
        self.federal_admin.set_federal_admin()

        # pending
        response = self.action_apply_response(client=self.client, _id=apply_id, action='pending')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyOrganization.Status.PENDING)

        # reject
        response = self.action_apply_response(client=self.client, _id=apply_id, action='reject')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyOrganization.Status.REJECT)

    def test_create_pending_pass_apply(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        # 联邦管理员权限
        self.client.logout()
        self.client.force_login(self.federal_admin)
        self.federal_admin.set_federal_admin()

        # pending
        response = self.action_apply_response(client=self.client, _id=apply_id, action='pending')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyOrganization.Status.PENDING)

        # pass
        response = self.action_apply_response(client=self.client, _id=apply_id, action='pass')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyOrganization.Status.PASS)
        apply = ApplyOrganization.objects.get(pk=apply_id)
        organization = DataCenter.objects.get(pk=apply.data_center_id)
        self.assertEqual(organization.name_en, apply.name_en)
        self.assertEqual(organization.name_en, self.apply_data['name_en'])
        self.assertEqual(organization.longitude, self.apply_data['longitude'])
        self.assertEqual(organization.longitude, apply.longitude)
        self.assertEqual(organization.latitude, self.apply_data['latitude'])
        self.assertEqual(organization.latitude, apply.latitude)
        self.assertIsInstance(organization, DataCenter)

    @staticmethod
    def list_response(client, queries: dict):
        url = reverse('api:apply-organization-list')
        if queries:
            query = parse.urlencode(queries, doseq=True)
            url = f'{url}?{query}'

        return client.get(url)

    @staticmethod
    def admin_list_response(client, queries: dict):
        url = reverse('api:apply-organization-admin-list')
        if queries:
            query = parse.urlencode(queries, doseq=True)
            url = f'{url}?{query}'

        return client.get(url)

    def test_list(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        # list
        response = self.list_response(client=self.client, queries={})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertKeysIn(keys=[
            'id', 'creation_time', 'status', 'user', 'deleted', 'name', "name_en", 'abbreviation',
            'independent_legal_person',
            'country', 'city', 'postal_code', 'address', 'endpoint_vms', 'endpoint_object',
            'endpoint_compute', 'endpoint_monitor', 'desc', 'logo_url', 'certification_url',
            "longitude", "latitude"
        ], container=response.data['results'][0])
        self.assert_is_subdict_of(sub={
            'status': ApplyOrganization.Status.WAIT, 'deleted': False,
            'name': '中国科学院计算机信息网络中心', "name_en": "cnic",
            'abbreviation': '中科院网络中心', 'independent_legal_person': True, 'country': '中国', 'city': '北京',
            'postal_code': '100083', 'address': '北京市海淀区', 'endpoint_vms': 'https://vms.cstcloud.cn/',
            'endpoint_object': '', 'endpoint_compute': '', 'endpoint_monitor': '', 'desc': 'test',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg',
            'certification_url': '/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx',
            "longitude": -88, "latitude": 66
        }, d=response.data['results'][0])

        # list
        response = self.list_response(client=self.client, queries={
            'status': ApplyOrganization.Status.CANCEL})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 0)

        # cancel
        url = reverse('api:apply-organization-action', kwargs={'id': apply_id, 'action': 'cancel'})
        response = self.client.post(url, data=apply_data)
        self.assertEqual(response.status_code, 200)
        # list cancel
        response = self.list_response(client=self.client, queries={
            'status': ApplyOrganization.Status.CANCEL})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)

        # list deleted
        response = self.list_response(client=self.client, queries={'deleted': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        # delete
        url = reverse('api:apply-organization-detail', kwargs={'id': apply_id})
        response = self.client.delete(url, data=apply_data)
        self.assertEqual(response.status_code, 204)
        # list deleted
        response = self.list_response(client=self.client, queries={'deleted': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        # admin user
        self.client.logout()
        self.client.force_login(self.federal_admin)
        # list
        response = self.list_response(client=self.client, queries={
            'status': [ApplyOrganization.Status.CANCEL, ApplyOrganization.Status.WAIT]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # admin-list
        response = self.admin_list_response(client=self.client, queries={})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.federal_admin.set_federal_admin()
        # admin-list
        response = self.admin_list_response(client=self.client, queries={})
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertKeysIn(keys=[
            'id', 'creation_time', 'status', 'user', 'deleted', 'name', "name_en", 'abbreviation',
            'independent_legal_person',
            'country', 'city', 'postal_code', 'address', 'endpoint_vms', 'endpoint_object',
            'endpoint_compute', 'endpoint_monitor', 'desc', 'logo_url', 'certification_url',
            "longitude", "latitude"
        ], container=response.data['results'][0])
        self.assert_is_subdict_of(sub={
            'status': ApplyOrganization.Status.CANCEL, 'deleted': True,
            'name': '中国科学院计算机信息网络中心', 'abbreviation': '中科院网络中心', "name_en": "cnic",
            'independent_legal_person': True, 'country': '中国', 'city': '北京',
            'postal_code': '100083', 'address': '北京市海淀区', 'endpoint_vms': 'https://vms.cstcloud.cn/',
            'endpoint_object': '', 'endpoint_compute': '', 'endpoint_monitor': '', 'desc': 'test',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg',
            'certification_url': '/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx',
            "longitude": -88, "latitude": 66
        }, d=response.data['results'][0])

        # admin-list deleted=False
        response = self.admin_list_response(client=self.client, queries={'deleted': False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # admin-list
        response = self.admin_list_response(client=self.client, queries={
            'status': [ApplyOrganization.Status.CANCEL, 'invalid']})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)


class ApplyVmServiceTests(MyAPITestCase):
    def setUp(self):
        self.user = None
        set_auth_header(self)
        self.federal_username = 'federal_admin'
        self.federal_password = 'federal_password'
        self.federal_admin = get_or_create_user(username=self.federal_username, password=self.federal_password)
        service = get_or_create_service()
        self.service = service
        self.apply_data = {
            "organization_id": "string",
            "name": "地球大数据",
            "name_en": "casearth data",
            "service_type": service.service_type,
            "cloud_type": service.cloud_type,
            "endpoint_url": service.endpoint_url,
            "region": "1",
            "api_version": "v3",
            "username": service.username,
            "password": service.raw_password(),
            "project_name": "project",
            "project_domain_name": "default",
            "user_domain_name": "default",
            "remarks": "string",
            "need_vpn": True,
            "vpn_endpoint_url": "",
            "vpn_api_version": "",
            "vpn_username": "",
            "vpn_password": "",
            "longitude": 0,
            "latitude": 0,
            "contact_person": "shun",
            "contact_email": "user@example.com",
            "contact_telephone": "string",
            "contact_fixed_phone": "string",
            "contact_address": "北京信息化大厦",
            "logo_url": "/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg"
        }

    @staticmethod
    def create_apply_response(client, data):
        url = reverse('api:apply-service-list')
        return client.post(url, data=data)

    def test_create_cancel_delete_apply(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        apply_data['cloud_type'] = ApplyVmService.CLoudType.HYBRID.value
        endpoint_url = apply_data['endpoint_url']

        apply_data['endpoint_url'] = "htts://1359.226.235.3"
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        apply_data['endpoint_url'] = endpoint_url
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertErrorResponse(status_code=404, code='OrganizationNotExists', response=response)

        apply_data['organization_id'] = self.service.org_data_center.organization_id
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'user', 'creation_time', 'approve_time', 'status', 'organization_id',
            'longitude', 'latitude', 'name', 'name_en', 'region', 'service_type', 'cloud_type', 'endpoint_url',
            'api_version', 'username', 'password', 'project_name', 'project_domain_name',
            'user_domain_name', 'need_vpn', 'vpn_endpoint_url', 'vpn_api_version',
            'vpn_username', 'vpn_password', 'deleted', 'contact_person', 'contact_email',
            'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'remarks', 'logo_url'], container=response.data)

        self.assert_is_subdict_of(sub={
            'status': 'wait',
            'organization_id': self.service.org_data_center.organization_id,
            'longitude': 0.0, 'latitude': 0.0, 'name': '地球大数据', "name_en": "casearth data",
            'region': '1', 'service_type': self.service.service_type,
            'cloud_type': ApplyVmService.CLoudType.HYBRID,
            'endpoint_url': self.service.endpoint_url,
            'api_version': 'v3',
            'username': self.service.username,
            'password': self.service.raw_password(),
            'project_name': apply_data['project_name'],
            'project_domain_name': apply_data['project_domain_name'],
            'user_domain_name': apply_data['user_domain_name'], 'need_vpn': True,
            'vpn_endpoint_url': '', 'vpn_api_version': '',
            'vpn_username': '', 'vpn_password': '', 'deleted': False,
            'contact_person': 'shun', 'contact_email': 'user@example.com',
            'contact_telephone': 'string', 'contact_fixed_phone': 'string',
            'contact_address': '北京信息化大厦', 'remarks': 'string',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg'}, d=response.data)

        apply_id = response.data['id']

        # cancel
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'cancel'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'user', 'creation_time', 'approve_time', 'status', 'organization_id',
            'longitude', 'latitude', 'name', 'name_en', 'region', 'service_type', 'cloud_type', 'endpoint_url',
            'api_version', 'username', 'password', 'project_name', 'project_domain_name',
            'user_domain_name', 'need_vpn', 'vpn_endpoint_url', 'vpn_api_version',
            'vpn_username', 'vpn_password', 'deleted', 'contact_person', 'contact_email',
            'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'remarks', 'logo_url'], container=response.data)
        self.assertEqual(response.data['status'], ApplyVmService.Status.CANCEL)

        # delete
        url = reverse('api:apply-service-detail', kwargs={'id': apply_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_pending_reject_apply(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        url = reverse('api:apply-service-list')
        apply_data['organization_id'] = self.service.org_data_center.organization_id
        response = self.client.post(url, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        self.client.logout()
        self.client.force_login(self.federal_admin)

        # pending
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'pending'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.federal_admin.set_federal_admin()  # 联邦管理员权限
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyVmService.Status.PENDING)

        # first_reject
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'first_reject'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyVmService.Status.FIRST_REJECT)

    def test_pending_test_pass_apply(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        url = reverse('api:apply-service-list')
        apply_data['organization_id'] = self.service.org_data_center.organization_id
        response = self.client.post(url, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        self.client.logout()
        self.client.force_login(self.federal_admin)
        self.federal_admin.set_federal_admin()  # 联邦管理员权限

        # pending
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'pending'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyVmService.Status.PENDING)

        # first_pass
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'first_pass'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyVmService.Status.FIRST_PASS)

        # test
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'test'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['apply', 'ok', 'message'], response.data)
        self.assertKeysIn(keys=[
            'id', 'user', 'creation_time', 'approve_time', 'status', 'organization_id',
            'longitude', 'latitude', 'name', 'name_en', 'region', 'service_type', 'cloud_type', 'endpoint_url',
            'api_version', 'username', 'password', 'project_name', 'project_domain_name',
            'user_domain_name', 'need_vpn', 'vpn_endpoint_url', 'vpn_api_version',
            'vpn_username', 'vpn_password', 'deleted', 'contact_person', 'contact_email',
            'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'remarks', 'logo_url'], container=response.data['apply'])

        if response.data['ok']:
            self.assertEqual(response.data['apply']['status'], ApplyVmService.Status.TEST_PASS)
        else:
            self.assertEqual(response.data['apply']['status'], ApplyVmService.Status.TEST_FAILED)
            print(response.data['message'])

        # pass
        self.service.delete()
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'pass'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ApplyVmService.Status.PASS)

        apply = ApplyVmService.objects.get(pk=response.data['id'])
        self.assertEqual(apply.name_en, self.apply_data['name_en'])
        service = ServiceConfig.objects.get(pk=apply.service_id)
        self.assert_is_subdict_of(sub=service.extra_params(), d=self.apply_data)
        self.assertEqual(service.users.filter(id=self.user.id).exists(), True)

    @staticmethod
    def list_response(client, queries: dict):
        url = reverse('api:apply-service-list')
        if queries:
            query = parse.urlencode(queries, doseq=True)
            url = f'{url}?{query}'

        return client.get(url)

    @staticmethod
    def admin_list_response(client, queries: dict):
        url = reverse('api:apply-service-admin-list')
        if queries:
            query = parse.urlencode(queries, doseq=True)
            url = f'{url}?{query}'

        return client.get(url)

    def test_list(self):
        apply_data = {k: self.apply_data[k] for k in self.apply_data.keys()}
        apply_data['organization_id'] = self.service.org_data_center.organization_id
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        # list
        response = self.list_response(client=self.client, queries={})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertKeysIn(keys=[
            'id', 'user', 'creation_time', 'approve_time', 'status', 'organization_id',
            'longitude', 'latitude', 'name', 'name_en', 'region', 'service_type', 'cloud_type', 'endpoint_url',
            'api_version', 'username', 'password', 'project_name', 'project_domain_name',
            'user_domain_name', 'need_vpn', 'vpn_endpoint_url', 'vpn_api_version',
            'vpn_username', 'vpn_password', 'deleted', 'contact_person', 'contact_email',
            'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'remarks', 'logo_url'], container=response.data['results'][0])
        self.assert_is_subdict_of(sub={
            'status': ApplyVmService.Status.WAIT,
            'organization_id': self.service.org_data_center.organization_id,
            'longitude': 0.0, 'latitude': 0.0, 'name': '地球大数据', "name_en": "casearth data",
            'region': '1', 'service_type': self.service.service_type,
            'cloud_type': self.service.cloud_type,
            'endpoint_url': self.service.endpoint_url,
            'api_version': 'v3',
            'username': self.service.username,
            'password': self.service.raw_password(),
            'project_name': apply_data['project_name'],
            'project_domain_name': apply_data['project_domain_name'],
            'user_domain_name': apply_data['user_domain_name'], 'need_vpn': True,
            'vpn_endpoint_url': '', 'vpn_api_version': '',
            'vpn_username': '', 'vpn_password': '', 'deleted': False,
            'contact_person': 'shun', 'contact_email': 'user@example.com',
            'contact_telephone': 'string', 'contact_fixed_phone': 'string',
            'contact_address': '北京信息化大厦', 'remarks': 'string',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg'},
            d=response.data['results'][0])

        # list
        response = self.list_response(client=self.client, queries={
            'status': [ApplyVmService.Status.CANCEL, ApplyVmService.Status.PASS]})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 0)

        # cancel
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'cancel'})
        response = self.client.post(url, data=apply_data)
        self.assertEqual(response.status_code, 200)
        # list cancel
        response = self.list_response(client=self.client, queries={
            'status': [ApplyVmService.Status.CANCEL]})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)

        # list organization cancel
        response = self.list_response(client=self.client, queries={
            'status': [ApplyVmService.Status.CANCEL],
            'organization': self.service.org_data_center.organization_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        response = self.list_response(client=self.client, queries={
            'status': [ApplyVmService.Status.CANCEL],
            'organization': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # list deleted
        response = self.list_response(client=self.client, queries={'deleted': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        # delete
        url = reverse('api:apply-service-detail', kwargs={'id': apply_id})
        response = self.client.delete(url, data=apply_data)
        self.assertEqual(response.status_code, 204)

        # list deleted
        response = self.list_response(client=self.client, queries={'deleted': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        # admin user
        self.client.logout()
        self.client.force_login(self.federal_admin)

        # list
        response = self.list_response(client=self.client, queries={
            'status': ApplyVmService.Status.CANCEL})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # admin-list
        response = self.admin_list_response(client=self.client, queries={})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.federal_admin.set_federal_admin()
        # admin-list
        response = self.admin_list_response(client=self.client, queries={})
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertKeysIn(keys=[
            'id', 'user', 'creation_time', 'approve_time', 'status', 'organization_id',
            'longitude', 'latitude', 'name', "name_en", 'region', 'service_type', 'cloud_type', 'endpoint_url',
            'api_version', 'username', 'password', 'project_name', 'project_domain_name',
            'user_domain_name', 'need_vpn', 'vpn_endpoint_url', 'vpn_api_version',
            'vpn_username', 'vpn_password', 'deleted', 'contact_person', 'contact_email',
            'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'remarks', 'logo_url'], container=response.data['results'][0])
        self.assert_is_subdict_of(sub={
            'status': ApplyVmService.Status.CANCEL,
            'organization_id': self.service.org_data_center.organization_id,
            'longitude': 0.0, 'latitude': 0.0, 'name': '地球大数据', "name_en": "casearth data",
            'region': '1', 'service_type': self.service.service_type,
            'cloud_type': self.service.cloud_type,
            'endpoint_url': self.service.endpoint_url,
            'api_version': 'v3',
            'username': self.service.username,
            'password': self.service.raw_password(),
            'project_name': apply_data['project_name'],
            'project_domain_name': apply_data['project_domain_name'],
            'user_domain_name': apply_data['user_domain_name'], 'need_vpn': True,
            'vpn_endpoint_url': '', 'vpn_api_version': '',
            'vpn_username': '', 'vpn_password': '', 'deleted': True,
            'contact_person': 'shun', 'contact_email': 'user@example.com',
            'contact_telephone': 'string', 'contact_fixed_phone': 'string',
            'contact_address': '北京信息化大厦', 'remarks': 'string',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg'}, d=response.data['results'][0])

        # admin-list deleted=False
        response = self.admin_list_response(client=self.client, queries={'deleted': False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # admin-list organization
        response = self.admin_list_response(client=self.client, queries={
            'deleted': True, 'organization': self.service.org_data_center.organization_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        # admin-list organization
        response = self.admin_list_response(client=self.client, queries={
            'deleted': True, 'organization': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        # admin-list
        response = self.admin_list_response(client=self.client, queries={
            'status': [ApplyVmService.Status.CANCEL, 'invalid']})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)


class VoTests(MyAPITestCase):
    def setUp(self):
        self.user = None
        set_auth_header(self)
        self.user2_username = 'user2'
        self.user2_password = 'user2password'
        self.user2 = get_or_create_user(username=self.user2_username, password=self.user2_password)

    @staticmethod
    def create_vo_response(client, name, company, description):
        url = reverse('api:vo-list')
        data = {
            'name': name,
            'company': company,
            'description': description
        }
        return client.post(url, data=data)

    @staticmethod
    def update_vo_response(client, vo_id: str, data):
        url = reverse('api:vo-detail', kwargs={'id': vo_id})
        return client.patch(url, data=data)

    @staticmethod
    def delete_vo_response(client, vo_id: str):
        url = reverse('api:vo-detail', kwargs={'id': vo_id})
        return client.delete(url)

    @staticmethod
    def list_response(client, queries: dict):
        url = reverse('api:vo-list')
        if queries:
            query = parse.urlencode(queries, doseq=True)
            url = f'{url}?{query}'

        return client.get(url)

    @staticmethod
    def add_members_response(client, vo_id: str, usernames: list):
        url = reverse('api:vo-vo-add-members', kwargs={'id': vo_id})
        return client.post(url, data={'usernames': usernames})

    @staticmethod
    def list_vo_members_response(client, vo_id: str):
        url = reverse('api:vo-vo-list-members', kwargs={'id': vo_id})
        return client.get(url)

    @staticmethod
    def remove_members_response(client, vo_id: str, usernames: list):
        url = reverse('api:vo-vo-remove-members', kwargs={'id': vo_id})
        return client.post(url, data={'usernames': usernames})

    @staticmethod
    def change_member_role_response(client, member_id: str, role: str):
        url = reverse('api:vo-vo-members-role', kwargs={'member_id': member_id, 'role': role})
        return client.post(url)

    def test_create_update_delete(self):
        data = {
            'name': 'test vo',
            'company': 'cnic',
            'description': '测试'
        }
        response = self.create_vo_response(client=self.client, name=data['name'],
                                           company=data['company'], description=data['description'])
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['id', 'name', 'company', 'description', 'creation_time',
                                'owner', 'status'], container=response.data)
        sub = {'status': 'active'}
        sub.update(data)
        self.assert_is_subdict_of(sub=sub, d=response.data)
        self.assert_is_subdict_of(sub={'id': self.user.id, 'username': self.user.username},
                                  d=response.data['owner'])
        vo_id = response.data['id']

        # update
        update_data = {
            'name': 'vo1', 'company': '网络中心', 'description': '测试666'
        }
        response = self.update_vo_response(client=self.client, vo_id=vo_id, data=update_data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['id', 'name', 'company', 'description', 'creation_time',
                                'owner', 'status'], container=response.data)
        self.assert_is_subdict_of(sub=update_data, d=response.data)

        vo = VirtualOrganization.objects.select_related('owner').filter(id=vo_id).first()
        self.assertEqual(vo.deleted, False)
        self.assertEqual(vo.name, update_data['name'])
        self.assertEqual(vo.company, update_data['company'])
        self.assertEqual(vo.description, update_data['description'])

        # delete
        vo_account = PaymentManager.get_vo_point_account(vo_id=vo_id)
        vo_account.balance = Decimal('-1')
        vo_account.save(update_fields=['balance'])
        response = self.delete_vo_response(client=self.client, vo_id=vo_id)
        self.assertErrorResponse(status_code=409, code='BalanceArrearage', response=response)

        vo_account.balance = Decimal('0')
        vo_account.save(update_fields=['balance'])
        response = self.delete_vo_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 204)
        vo.refresh_from_db()
        self.assertEqual(vo.deleted, True)

    def test_list(self):
        data = {
            'name': 'test vo',
            'company': 'cnic',
            'description': '测试'
        }
        response = self.create_vo_response(client=self.client, name=data['name'],
                                           company=data['company'], description=data['description'])
        self.assertEqual(response.status_code, 200)

        # list
        response = self.list_response(client=self.client, queries={})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertKeysIn(keys=['id', 'name', 'company', 'description', 'creation_time',
                                'owner', 'status'], container=response.data['results'][0])

        # list as member
        response = self.list_response(client=self.client, queries={'member': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # list as owner
        response = self.list_response(client=self.client, queries={'owner': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

        # list as owner and member
        response = self.list_response(client=self.client, queries={'owner': '', 'member': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

        # query "name"
        response = self.list_response(client=self.client, queries={'name': 'ss'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        response = self.list_response(client=self.client, queries={'name': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

        # --------admin test----------
        self.client.logout()
        self.client.force_login(self.user2)
        response = self.list_response(client=self.client, queries={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        response = self.list_response(client=self.client, queries={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user2.set_federal_admin()
        response = self.list_response(client=self.client, queries={'as-admin': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_owner_members_action(self):
        """
        组长管理组测试
        """
        usernames = ['user-test1', 'user-test2']
        get_or_create_user(username=usernames[0], password='password')
        get_or_create_user(username=usernames[1], password='password')

        owner = self.user
        data = {
            'name': 'test vo',
            'company': 'cnic',
            'description': '测试'
        }
        response = self.create_vo_response(client=self.client, name=data['name'],
                                           company=data['company'], description=data['description'])
        self.assertEqual(response.status_code, 200)
        vo_id = response.data['id']

        # add members
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames + [owner.username])
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames + ['notfound'])
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['success', 'failed'], response.data)
        self.assertIsInstance(response.data['success'], list)
        self.assertEqual(len(response.data['success']), 2)
        self.assertKeysIn(['id', 'user', 'role', 'join_time', 'inviter'], response.data['success'][0])
        self.assertIn(response.data['success'][0]['user']['username'], usernames)
        self.assertEqual(response.data['success'][0]['role'], VoMember.Role.MEMBER)
        self.assertEqual(response.data['success'][0]['inviter'], owner.username)

        self.assertIsInstance(response.data['failed'], list)
        self.assertEqual(len(response.data['failed']), 1)
        self.assertEqual(response.data['failed'][0]['username'], 'notfound')

        # list members
        response = self.list_vo_members_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['members', 'owner'], response.data)
        self.assertIsInstance(response.data['members'], list)
        self.assertEqual(len(response.data['members']), 2)
        self.assertKeysIn(['id', 'user', 'role', 'join_time', 'inviter'], response.data['members'][0])
        self.assertEqual(response.data['owner'], {'id': owner.id, 'username': owner.username})

        # remove members
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=usernames[0:1])
        self.assertEqual(response.status_code, 204)

        # list members
        response = self.list_vo_members_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['members', 'owner'], response.data)
        self.assertEqual(len(response.data['members']), 1)
        self.assertKeysIn(['id', 'user', 'role', 'join_time', 'inviter'], response.data['members'][0])
        self.assertEqual(response.data['members'][0]['user']['username'], usernames[1])
        self.assert_is_subdict_of(sub={'role': VoMember.Role.MEMBER, 'inviter': owner.username},
                                  d=response.data['members'][0])

    def test_role_members_actions(self):
        """
        组角色管理组测试
        """
        usernames = ['user-test1', 'user-test2']
        get_or_create_user(username=usernames[0], password='password')
        get_or_create_user(username=usernames[1], password='password')

        owner = self.user
        data = {
            'name': 'test vo',
            'company': 'cnic',
            'description': '测试'
        }
        response = self.create_vo_response(client=self.client, name=data['name'],
                                           company=data['company'], description=data['description'])
        self.assertEqual(response.status_code, 200)
        vo_id = response.data['id']

        # add member user2
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=[self.user2.username])
        self.assertEqual(response.status_code, 200)
        user2_member_id = response.data['success'][0]['id']

        # add member test1
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames[0:1])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['success']), 1)
        test1_member_id = response.data['success'][0]['id']

        # member role no permission add member
        # login user2
        self.client.logout()
        self.client.force_login(self.user2)
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames)
        self.assertErrorResponse(response=response, status_code=403, code='AccessDenied')

        # user2 no permission set leader role
        response = self.change_member_role_response(client=self.client, member_id=user2_member_id,
                                                    role=VoMember.Role.LEADER)
        self.assertErrorResponse(response=response, status_code=403, code='AccessDenied')
        # login owner
        self.client.logout()
        self.client.force_login(owner)
        # owner set user2 leader role
        response = self.change_member_role_response(client=self.client, member_id=user2_member_id,
                                                    role=VoMember.Role.LEADER)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'user', 'role', 'join_time', 'inviter'], response.data)
        self.assertEqual(response.data['role'], VoMember.Role.LEADER)

        # owner set test1 role leader
        response = self.change_member_role_response(client=self.client, member_id=test1_member_id,
                                                    role=VoMember.Role.LEADER)
        self.assertEqual(response.status_code, 200)

        # login leader user
        self.client.logout()
        self.client.force_login(self.user2)

        # leader role add member test2
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames[1:2])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['success']), 1)
        self.assertEqual(len(response.data['failed']), 0)

        # list members
        response = self.list_vo_members_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['members', 'owner'], response.data)
        self.assertEqual(len(response.data['members']), 3)
        member_usernames = usernames + [self.user2.username]
        for m in response.data['members']:
            un = m['user']['username']
            self.assertIn(un, member_usernames)
            member_usernames.remove(un)
        self.assertFalse(member_usernames)

        # leader role no permission remove leader role member test1
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=usernames[0:1])
        self.assertErrorResponse(response=response, status_code=403, code='AccessDenied')

        # leader role remove member test2
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=usernames[1:2])
        self.assertEqual(response.status_code, 204)

        # owner remove leader role member test1
        # login owner
        self.client.logout()
        self.client.force_login(owner)
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=usernames[0:1])
        self.assertEqual(response.status_code, 204)

        # list members
        response = self.list_vo_members_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['members', 'owner'], response.data)
        self.assertEqual(len(response.data['members']), 1)
        self.assertEqual(response.data['members'][0]['user']['username'], self.user2.username)

        # owner remove owner
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=[owner.username])
        self.assertErrorResponse(response=response, status_code=403, code='AccessDenied')

    def test_vo_statistic(self):
        vo1 = VirtualOrganization(
            name='test vo1', owner=self.user2
        )
        vo1.save(force_insert=True)

        url = reverse('api:vo-vo-statistic', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        url = reverse('api:vo-vo-statistic', kwargs={'id': vo1.id})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        member = VoMember(user_id=self.user.id, vo_id=vo1.id, role=VoMember.Role.LEADER.value)
        member.save(force_insert=True)

        url = reverse('api:vo-vo-statistic', kwargs={'id': vo1.id})
        r = self.client.get(url)
        self.assertKeysIn(keys=[
            'vo', 'member_count', 'server_count', 'order_count', 'coupon_count', 'balance'], container=r.data)
        self.assertEqual(r.data['vo']['id'], vo1.id)
        self.assertEqual(r.data['member_count'], 2)
        self.assertEqual(r.data['server_count'], 0)
        self.assertEqual(r.data['order_count'], 0)
        self.assertEqual(r.data['coupon_count'], 0)
        self.assertEqual(r.data['balance'], '0.00')

        vo1_account = PaymentManager.get_vo_point_account(vo_id=vo1.id)
        vo1_account.balance = Decimal('-1.23')
        vo1_account.save(update_fields=['balance'])

        order_instance_config = ServerConfig(
            vm_cpu=2, vm_ram=2048, systemdisk_size=100, public_ip=True,
            image_id='image_id', image_name='', network_id='network_id', network_name='',
            azone_id='azone_id', azone_name='azone_name', flavor_id=''
        )
        order1, resource1 = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id='test',
            service_id='test',
            service_name='test',
            resource_type=ResourceType.VM.value,
            instance_config=order_instance_config,
            period=2,
            pay_type=PayType.POSTPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='', vo_name='',
            owner_type=OwnerType.USER.value
        )

        order2, resource2 = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id='test',
            service_id='test',
            service_name='test',
            resource_type=ResourceType.VM.value,
            instance_config=order_instance_config,
            period=2,
            pay_type=PayType.POSTPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=vo1.id, vo_name=vo1.name,
            owner_type=OwnerType.VO.value
        )
        from .test_disk import create_disk_metadata
        create_disk_metadata(
            service_id=None, azone_id='2', disk_size=88, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=None
        )
        create_disk_metadata(
            service_id=None, azone_id='1', disk_size=886, pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.VO.value, user_id=self.user2.id, vo_id=vo1.id,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=None
        )

        url = reverse('api:vo-vo-statistic', kwargs={'id': vo1.id})
        r = self.client.get(url)
        self.assertKeysIn(keys=[
            'vo', 'member_count', 'server_count', 'order_count', 'coupon_count', 'balance',
            'my_role', 'disk_count'
        ], container=r.data)
        self.assertEqual(r.data['vo']['id'], vo1.id)
        self.assertEqual(r.data['member_count'], 2)
        self.assertEqual(r.data['server_count'], 0)
        self.assertEqual(r.data['order_count'], 1)
        self.assertEqual(r.data['coupon_count'], 0)
        self.assertEqual(r.data['balance'], '-1.23')
        self.assertEqual(r.data['my_role'], VoMember.Role.LEADER.value)
        self.assertEqual(r.data['disk_count'], 1)
