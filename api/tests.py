import hashlib
import collections
import io
import random
from string import printable
from datetime import timedelta
from urllib import parse

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from servers.models import Flavor, Server
from service.managers import UserQuotaManager
from service.models import ApplyOrganization, DataCenter, ApplyVmService, ServiceConfig
from applyment.models import ApplyQuota
from utils.test import get_or_create_user, get_or_create_service, get_or_create_center
from adapters import outputs
from vo.models import VirtualOrganization, VoMember


def random_string(length: int = 10):
    return random.choices(printable, k=length)


def random_bytes_io(mb_num: int):
    bio = io.BytesIO()
    for i in range(1024):           # MB
        s = ''.join(random_string(mb_num))
        b = s.encode() * 1024         # KB
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


def chunks(f, chunk_size=2*2**20):
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


def create_server_metadata(service, user, user_quota):
    server = Server(service=service,
                    instance_id='test',
                    remarks='',
                    user=user,
                    vcpus=2,
                    ram=1024,
                    ipv4='127.0.0.1',
                    image='test-image',
                    task_status=Server.TASK_CREATED_OK,
                    user_quota=user_quota,
                    public_ip=False)
    server.save()
    return server


class MyAPITestCase(APITestCase):
    def assertKeysIn(self, keys: list, container):
        for k in keys:
            self.assertIn(k, container)

    def assertErrorResponse(self, status_code: int, code: str, response):
        self.assertEqual(response.status_code, status_code)
        self.assertKeysIn(['code', 'message'], response.data)
        self.assertEqual(response.data['code'], code)

    def assert_is_subdict_of(self, sub: dict, d: dict):
        for k, v in sub.items():
            if k in d and v == d[k]:
                continue
            else:
                self.fail(f'{sub} is not sub dict of {d}, Not Equal key is {k}')

        return True


def set_auth_header(test_case: APITestCase):
    password = 'password'
    user = get_or_create_user(password=password)
    # token = AccessToken.for_user(user)
    # test_case.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
    test_case.client.force_login(user=user)
    test_case.user = user


class FlavorTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)

    def test_get_flavor(self):
        f = Flavor(vcpus=1, ram=1024, enable=True)
        f.save()
        url = reverse('api:flavor-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'flavors': [{
            'id': f.id, 'vcpus': f.vcpus, 'ram': 1024
        }]})


class UserQuotaTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        mgr = UserQuotaManager()
        self.quota = mgr.create_quota(user=self.user, service=self.service)
        self.expire_quota = mgr.create_quota(user=self.user, service=self.service,
                                             expire_time=timezone.now() - timedelta(days=1))

        create_server_metadata(
            service=self.service, user=self.user, user_quota=self.quota)

    def test_list_delete_quota(self):
        url = reverse('api:user-quota-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'results', "next", "previous"], response.data)
        self.assertEqual(response.data['count'], 2)

        url += f'?usable=true'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'results', "next", "previous"], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertKeysIn(["id", "tag", "user", "service", "private_ip_total",
                           "private_ip_used", "public_ip_total", "public_ip_used",
                           "vcpu_total", "vcpu_used", "ram_total", "ram_used",
                           "disk_size_total", "disk_size_used", "expiration_time",
                           "deleted", "display"], response.data['results'][0])

        # delete
        url = reverse('api:user-quota-detail', kwargs={'id': self.quota.id})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, 204)

        url = reverse('api:user-quota-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_list_quota_servers(self):
        url = reverse('api:user-quota-quota-servers', kwargs={'id': 'notfound'})
        response = self.client.get(url, format='json')
        self.assertErrorResponse(status_code=404, response=response, code='NotFound')

        url = reverse('api:user-quota-quota-servers', kwargs={'id': self.quota.id})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'results', "next", "previous"], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time",
                           "remarks"], response.data['results'][0])


class ServersTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.miss_server = create_server_metadata(
            service=self.service, user=self.user, user_quota=None)

    def test_server_create(self):
        url = reverse('api:servers-list')
        response = self.client.post(url, data={})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        response = self.client.post(url, data={
            'service_id': 'sss', 'image_id': 'aaa', 'flavor_id': 'xxx', 'quota_id': 'sss'})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

    def test_server_remark(self):
        url = reverse('api:servers-server-remark', kwargs={'id': self.miss_server.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, 400)

        url = reverse('api:servers-server-remark', kwargs={'id': '00'})
        url += f'?remark=ss'
        response = self.client.patch(url)
        self.assertEqual(response.status_code, 404)

        remark = 'test-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.miss_server.id})
        url += f'?remark={remark}'
        response = self.client.patch(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.miss_server.refresh_from_db()
        self.assertEqual(remark, self.miss_server.remarks)

    def test_server_status(self):
        url = reverse('api:servers-server_status', kwargs={'id': self.miss_server.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        url = reverse('api:servers-server_status', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertKeysIn(['code', 'message'], response.data)
        self.assertEqual(response.data['code'], 'NotFound')

    def test_server_detail(self):
        url = reverse('api:servers-detail', kwargs={'id': 'motfound'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertKeysIn(['code', 'message'], response.data)
        self.assertEqual(response.data['code'], 'NotFound')

        url = reverse('api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "endpoint_url", "service", "user_quota",
                           "center_quota"], response.data['server'])

    def test_server_list(self):
        url = reverse('api:servers-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertIsInstance(response.data['servers'], list)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time",
                           "remarks", "endpoint_url", "service", "user_quota",
                           "center_quota"], response.data['servers'][0])

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

    def tearDown(self):
        url = reverse('api:servers-detail', kwargs={'id': 'motfound'})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        url = reverse('api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        self.list_service_test_case()

    def list_service_test_case(self):
        url = reverse('api:server-archive-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time",
                           "remarks", "service", "user_quota",
                           "center_quota", "deleted_time"], response.data["results"][0])


class ServiceTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.service = get_or_create_service()

    def test_list_service(self):
        url = reverse('api:service-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertKeysIn(["id", "name", "service_type", "add_time",
                           "need_vpn", "status", "data_center"], response.data["results"][0])
        self.assertIsInstance(response.data["results"][0]['status'], str)

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
        self.assertKeysIn(["id", "name", "service_type", "add_time",
                           "need_vpn", "status", "data_center"], response.data["results"][0])
        self.assertIsInstance(response.data["results"][0]['status'], str)

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
                           "creation_time", "desc"], response.data[0])


class NetworkTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()

    def test_list_network(self):
        url = reverse('api:networks-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        url += f'?service_id={self.service.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertKeysIn(["id", "name", "public", "segment"], response.data[0])

        network_id = response.data[0]['id']
        url = reverse('api:networks-detail', kwargs={'network_id': network_id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        url += f'?service_id={self.service.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "name", "public", "segment"], response.data)


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
        self.assertKeysIn(["id", "name", "endpoint_vms", "endpoint_object", "endpoint_compute",
                           "endpoint_monitor", "creation_time", "status", "desc"],
                          response.data['registries'][0])


class UserQuotaApplyTests(MyAPITestCase):
    old_private_ip = 1
    old_public_ip = 2
    old_vcpu = 6
    old_ram = 8192
    old_disk_size = 2
    old_duration_days = 10

    new_private_ip = 6
    new_public_ip = 1
    new_vcpu = 6
    new_ram = 4096
    new_disk_size = 0
    new_duration_days = 100

    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()

    def create_apply(self):
        url = reverse('api:apply-quota-list')
        response = self.client.post(url, data={
            'service_id': self.service.id,
            'private_ip': self.old_private_ip,
            'public_ip': self.old_public_ip,
            'vcpu': self.old_vcpu,
            'ram': self.old_ram,  # Mb
            'disk_size': self.old_disk_size,
            'duration_days': self.old_duration_days,
            'company': 'cnic',
            'contact': '666',
            'purpose': 'test'
        })
        return response

    def update_apply(self, apply_id):
        url = reverse('api:apply-quota-detail', kwargs={'apply_id': apply_id})
        response = self.client.patch(url, data={
            'private_ip': self.new_private_ip,
            'public_ip': self.new_public_ip,
            'vcpu': self.new_vcpu,
            'ram': self.new_ram,  # Mb
            'disk_size': self.new_disk_size,
            'duration_days': self.new_duration_days,
            'company': 'cnic',
            'contact': '666',
            'purpose': 'test'
        })
        return response

    def pending_apply(self, apply_id):
        url = reverse('api:apply-quota-pending_apply', kwargs={'apply_id': apply_id})
        return self.client.post(url)

    def cancel_apply(self, apply_id):
        url = reverse('api:apply-quota-cancel_apply', kwargs={'apply_id': apply_id})
        return self.client.post(url)

    def reject_apply(self, apply_id):
        url = reverse('api:apply-quota-reject_apply', kwargs={'apply_id': apply_id})
        return self.client.post(url)

    def pass_apply(self, apply_id):
        url = reverse('api:apply-quota-pass_apply', kwargs={'apply_id': apply_id})
        return self.client.post(url)

    def delete_apply(self, apply_id):
        url = reverse('api:apply-quota-detail', kwargs={'apply_id': apply_id})
        return self.client.delete(url)

    def apply_response_data_keys_assert(self, data):
        self.assertKeysIn(["id", "private_ip", "public_ip", "vcpu",
                           "ram", "disk_size", "duration_days", "company",
                           "contact", "purpose", "creation_time", "status",
                           "service"], data)

    def test_create_delete_apply(self):
        response = self.create_apply()
        self.assertEqual(response.status_code, 201)
        self.apply_response_data_keys_assert(response.data)
        apply_id = response.data['id']

        response = self.delete_apply(apply_id)
        self.assertEqual(response.status_code, 204)

        base_url = reverse('api:apply-quota-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)
        self.apply_response_data_keys_assert(response.data['results'][0])
        self.assertEqual(response.data['results'][0]['status'], 'wait')
        self.assertEqual(response.data['results'][0]['deleted'], True)

    def test_create_modify_cancel_apply(self):
        response = self.create_apply()
        self.assertEqual(response.status_code, 201)
        self.apply_response_data_keys_assert(response.data)
        self.assertEqual(response.data['service']['id'], self.service.id)
        self.assertEqual(response.data['private_ip'], self.old_private_ip)
        self.assertEqual(response.data['public_ip'], self.old_public_ip)
        self.assertEqual(response.data['vcpu'], self.old_vcpu)
        self.assertEqual(response.data['ram'], self.old_ram)
        self.assertEqual(response.data['disk_size'], self.old_disk_size)
        self.assertEqual(response.data['duration_days'], self.old_duration_days)
        self.assertEqual(response.data['company'], 'cnic')
        self.assertEqual(response.data['contact'], '666')
        self.assertEqual(response.data['purpose'], 'test')

        apply_id = response.data['id']
        response = self.update_apply(apply_id)
        self.assertEqual(response.status_code, 200)
        self.apply_response_data_keys_assert(response.data)
        self.assertEqual(response.data['service']['id'], self.service.id)
        self.assertEqual(response.data['private_ip'], self.new_private_ip)
        self.assertEqual(response.data['public_ip'], self.new_public_ip)
        self.assertEqual(response.data['vcpu'], self.new_vcpu)
        self.assertEqual(response.data['ram'], self.new_ram)
        self.assertEqual(response.data['disk_size'], self.new_disk_size)
        self.assertEqual(response.data['duration_days'], self.new_duration_days)
        self.assertEqual(response.data['company'], 'cnic')
        self.assertEqual(response.data['contact'], '666')
        self.assertEqual(response.data['purpose'], 'test')
        self.assertEqual(response.data['status'], 'wait')

        response = self.pending_apply(apply_id)
        self.assertEqual(response.status_code, 403)

        response = self.cancel_apply(apply_id)
        self.assertEqual(response.status_code, 200)

        url = reverse('api:apply-quota-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data['count'], 1)
        self.apply_response_data_keys_assert(response.data['results'][0])
        self.assertEqual(response.data['results'][0]['status'], 'cancel')

    def test_perms_pass_apply(self):
        response = response = self.create_apply()
        self.assertEqual(response.status_code, 201)
        apply_id = response.data['id']

        response = self.pending_apply(apply_id)
        self.assertEqual(response.status_code, 403)

        self.service.users.add(self.user)   # 加管理权限

        response = self.pending_apply(apply_id)
        self.assertEqual(response.status_code, 200)
        self.apply_response_data_keys_assert(response.data)

        response = self.pass_apply(apply_id)
        self.assertEqual(response.status_code, 200)

        response = self.update_apply(apply_id)
        self.assertEqual(response.status_code, 409)     # 审批后不可修改

        apply = ApplyQuota.objects.get(pk=apply_id)
        self.assertEqual(apply.status, apply.STATUS_PASS)

        quota = apply.user_quota
        self.assertEqual(quota.private_ip_total, self.old_private_ip)
        self.assertEqual(quota.public_ip_total, self.old_public_ip)
        self.assertEqual(quota.vcpu_total, self.old_vcpu)
        self.assertEqual(quota.ram_total, self.old_ram)
        self.assertEqual(quota.disk_size_total, self.old_disk_size)
        self.assertEqual(quota.duration_days, self.old_duration_days)

    def test_perms_reject_apply(self):
        response = response = self.create_apply()
        self.assertEqual(response.status_code, 201)
        apply_id = response.data['id']
        self.service.users.add(self.user)  # 加管理权限

        response = self.pending_apply(apply_id)
        self.assertEqual(response.status_code, 200)
        self.apply_response_data_keys_assert(response.data)

        response = self.reject_apply(apply_id)
        self.assertEqual(response.status_code, 200)

        apply = ApplyQuota.objects.get(pk=apply_id)
        self.assertEqual(apply.status, apply.STATUS_REJECT)

    def test_apply_status_conflict(self):
        response = response = self.create_apply()
        self.assertEqual(response.status_code, 201)
        apply_id = response.data['id']
        self.service.users.add(self.user)  # 加管理权限

        # wait !=> pass
        response = self.pass_apply(apply_id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'Conflict')

        # wait !=> reject
        response = self.reject_apply(apply_id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'Conflict')

        # wait => pending
        response = self.pending_apply(apply_id)
        self.assertEqual(response.status_code, 200)

        # pending !=> update
        response = self.update_apply(apply_id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'Conflict')

        # pending !=> cancel
        response = self.cancel_apply(apply_id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'Conflict')

        # pending => reject
        response = self.reject_apply(apply_id)
        self.assertEqual(response.status_code, 200)

        # reject !=> cancel
        response = self.cancel_apply(apply_id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'Conflict')

        # reject !=> update
        response = self.update_apply(apply_id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'Conflict')

        # reject !=> pass
        response = self.pass_apply(apply_id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'Conflict')

    def list_apply_query_params(self, base_url, apply_id):
        # query param "service_id"
        query = parse.urlencode({'service': 'test'})
        url = f'{base_url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 0)

        query = parse.urlencode({'service': self.service.id})
        url = f'{base_url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)

        # query param "deleted"
        url = f'{base_url}?deleted=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 0)

        url = f'{base_url}?deleted=false'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)

        # query param "status"
        query_dict = {'status': ['pending', 'pass']}
        query = parse.urlencode(query_dict, doseq=True)
        url = f'{base_url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 0)

        query_dict = {'status': ['wait']}
        query = parse.urlencode(query_dict, doseq=True)
        url = f'{base_url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)

        self.cancel_apply(apply_id)
        query_dict = {'status': ['cancel', 'pass']}
        query = parse.urlencode(query_dict, doseq=True)
        url = f'{base_url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_admin_list_apply(self):
        response = response = self.create_apply()
        self.assertEqual(response.status_code, 201)
        apply_id = response.data['id']

        base_url = reverse('api:apply-quota-admin-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 0)

        self.service.users.add(self.user)  # 加管理权限

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)
        self.apply_response_data_keys_assert(response.data['results'][0])
        self.assertEqual(response.data['results'][0]['status'], 'wait')

        self.list_apply_query_params(base_url=base_url, apply_id=apply_id)

    def test_list_apply(self):
        response = response = self.create_apply()
        self.assertEqual(response.status_code, 201)
        apply_id = response.data['id']

        base_url = reverse('api:apply-quota-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)
        self.apply_response_data_keys_assert(response.data['results'][0])
        self.assertEqual(response.data['results'][0]['status'], 'wait')

        self.list_apply_query_params(base_url=base_url, apply_id=apply_id)


class UserTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()

    def test_account(self):
        base_url = reverse('api:user-account')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "username", "fullname", "role"], response.data)

        self.assertEqual(response.data['id'], self.user.id)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['fullname'], self.user.get_full_name())
        self.assertEqual(response.data['role'], self.user.role)


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
        "certification_url": "/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx"
    }

    def setUp(self):
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
            'id', 'creation_time', 'status', 'user', 'deleted', 'name', 'abbreviation', 'independent_legal_person',
            'country', 'city', 'postal_code', 'address', 'endpoint_vms', 'endpoint_object',
            'endpoint_compute', 'endpoint_monitor', 'desc', 'logo_url', 'certification_url'
        ], container=response.data)
        self.assert_is_subdict_of(sub={
            'status': 'wait', 'deleted': False, 'name': '中国科学院计算机信息网络中心',
            'abbreviation': '中科院网络中心', 'independent_legal_person': True, 'country': '中国', 'city': '北京',
            'postal_code': '100083', 'address': '北京市海淀区', 'endpoint_vms': 'https://vms.cstcloud.cn/',
            'endpoint_object': '', 'endpoint_compute': '', 'endpoint_monitor': '', 'desc': 'test',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg',
            'certification_url': '/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx'
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
            'id', 'creation_time', 'status', 'user', 'deleted', 'name', 'abbreviation', 'independent_legal_person',
            'country', 'city', 'postal_code', 'address', 'endpoint_vms', 'endpoint_object',
            'endpoint_compute', 'endpoint_monitor', 'desc', 'logo_url', 'certification_url'
        ], container=response.data['results'][0])
        self.assert_is_subdict_of(sub={
            'status': ApplyOrganization.Status.WAIT, 'deleted': False, 'name': '中国科学院计算机信息网络中心',
            'abbreviation': '中科院网络中心', 'independent_legal_person': True, 'country': '中国', 'city': '北京',
            'postal_code': '100083', 'address': '北京市海淀区', 'endpoint_vms': 'https://vms.cstcloud.cn/',
            'endpoint_object': '', 'endpoint_compute': '', 'endpoint_monitor': '', 'desc': 'test',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg',
            'certification_url': '/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx'
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
            'id', 'creation_time', 'status', 'user', 'deleted', 'name', 'abbreviation', 'independent_legal_person',
            'country', 'city', 'postal_code', 'address', 'endpoint_vms', 'endpoint_object',
            'endpoint_compute', 'endpoint_monitor', 'desc', 'logo_url', 'certification_url'
        ], container=response.data['results'][0])
        self.assert_is_subdict_of(sub={
            'status': ApplyOrganization.Status.CANCEL, 'deleted': True,
            'name': '中国科学院计算机信息网络中心', 'abbreviation': '中科院网络中心',
            'independent_legal_person': True, 'country': '中国', 'city': '北京',
            'postal_code': '100083', 'address': '北京市海淀区', 'endpoint_vms': 'https://vms.cstcloud.cn/',
            'endpoint_object': '', 'endpoint_compute': '', 'endpoint_monitor': '', 'desc': 'test',
            'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg',
            'certification_url': '/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx'
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
        set_auth_header(self)
        self.federal_username = 'federal_admin'
        self.federal_password = 'federal_password'
        self.federal_admin = get_or_create_user(username=self.federal_username, password=self.federal_password)
        service = get_or_create_service()
        self.service = service
        self.apply_data = {
            "organization_id": "string",
            "name": "地球大数据",
            "service_type": service.service_type,
            "endpoint_url": service.endpoint_url,
            "region": "1",
            "api_version": "v3",
            "username": service.username,
            "password": service.raw_password(),
            "project_name": "",
            "project_domain_name": "",
            "user_domain_name": "",
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
        endpoint_url = apply_data['endpoint_url']

        apply_data['endpoint_url'] = "htts://1359.226.235.3"
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        apply_data['endpoint_url'] = endpoint_url
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertErrorResponse(status_code=404, code='OrganizationNotExists', response=response)

        apply_data['organization_id'] = self.service.data_center_id
        response = self.create_apply_response(client=self.client, data=apply_data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'user', 'creation_time', 'approve_time', 'status', 'organization_id',
            'longitude', 'latitude', 'name', 'region', 'service_type', 'endpoint_url',
            'api_version', 'username', 'password', 'project_name', 'project_domain_name',
            'user_domain_name', 'need_vpn', 'vpn_endpoint_url', 'vpn_api_version',
            'vpn_username', 'vpn_password', 'deleted', 'contact_person', 'contact_email',
            'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'remarks', 'logo_url'], container=response.data)

        self.assert_is_subdict_of(sub={
            'status': 'wait',
            'organization_id': self.service.data_center_id,
            'longitude': 0.0, 'latitude': 0.0, 'name': '地球大数据',
            'region': '1', 'service_type': self.service.service_type,
            'endpoint_url': self.service.endpoint_url,
            'api_version': 'v3',
            'username': self.service.username,
            'password': self.service.raw_password(),
            'project_name': '',
            'project_domain_name': '',
            'user_domain_name': '', 'need_vpn': True,
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
            'longitude', 'latitude', 'name', 'region', 'service_type', 'endpoint_url',
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
        apply_data['organization_id'] = self.service.data_center_id
        response = self.client.post(url, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        self.client.logout()
        self.client.force_login(self.federal_admin)

        # pending
        url = reverse('api:apply-service-action', kwargs={'id': apply_id, 'action': 'pending'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.federal_admin.set_federal_admin()      # 联邦管理员权限
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
        apply_data['organization_id'] = self.service.data_center_id
        response = self.client.post(url, data=apply_data)
        self.assertEqual(response.status_code, 200)
        apply_id = response.data['id']

        self.client.logout()
        self.client.force_login(self.federal_admin)
        self.federal_admin.set_federal_admin()      # 联邦管理员权限

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
            'longitude', 'latitude', 'name', 'region', 'service_type', 'endpoint_url',
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
        service = ServiceConfig.objects.get(pk=apply.service_id)
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
        apply_data['organization_id'] = self.service.data_center_id
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
            'longitude', 'latitude', 'name', 'region', 'service_type', 'endpoint_url',
            'api_version', 'username', 'password', 'project_name', 'project_domain_name',
            'user_domain_name', 'need_vpn', 'vpn_endpoint_url', 'vpn_api_version',
            'vpn_username', 'vpn_password', 'deleted', 'contact_person', 'contact_email',
            'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'remarks', 'logo_url'], container=response.data['results'][0])
        self.assert_is_subdict_of(sub={
            'status': ApplyVmService.Status.WAIT,
            'organization_id': self.service.data_center_id,
            'longitude': 0.0, 'latitude': 0.0, 'name': '地球大数据',
            'region': '1', 'service_type': self.service.service_type,
            'endpoint_url': self.service.endpoint_url,
            'api_version': 'v3',
            'username': self.service.username,
            'password': self.service.raw_password(),
            'project_name': '',
            'project_domain_name': '',
            'user_domain_name': '', 'need_vpn': True,
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
            'organization': self.service.data_center_id})
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
            'longitude', 'latitude', 'name', 'region', 'service_type', 'endpoint_url',
            'api_version', 'username', 'password', 'project_name', 'project_domain_name',
            'user_domain_name', 'need_vpn', 'vpn_endpoint_url', 'vpn_api_version',
            'vpn_username', 'vpn_password', 'deleted', 'contact_person', 'contact_email',
            'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'remarks', 'logo_url'], container=response.data['results'][0])
        self.assert_is_subdict_of(sub={
            'status': ApplyVmService.Status.CANCEL,
            'organization_id': self.service.data_center_id,
            'longitude': 0.0, 'latitude': 0.0, 'name': '地球大数据',
            'region': '1', 'service_type': self.service.service_type,
            'endpoint_url': self.service.endpoint_url,
            'api_version': 'v3',
            'username': self.service.username,
            'password': self.service.raw_password(),
            'project_name': '',
            'project_domain_name': '',
            'user_domain_name': '', 'need_vpn': True,
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
            'deleted': True, 'organization': self.service.data_center_id})
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
        url = reverse('api:vo-vo-members-role', kwargs={'member_id': member_id, 'role':role})
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
        self.assertKeysIn(keys=['id', 'name', 'company','description', 'creation_time',
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
        self.assertEqual(vo.name, update_data['name'])
        self.assertEqual(vo.company, update_data['company'])
        self.assertEqual(vo.description, update_data['description'])

        # delete
        response = self.delete_vo_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 204)

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
