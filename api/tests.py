from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from servers.models import Flavor, Server
from service.managers import UserQuotaManager
from applyment.models import ApplyQuota
from utils.test import get_or_create_user, get_or_create_service, get_or_create_center
from adapters import outputs


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

    def test_list_quota(self):
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
        self.user = get_or_create_user()
        self.service = get_or_create_service()

    def test_list_service(self):
        url = reverse('api:service-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertKeysIn(["id", "name", "service_type", "add_time",
                           "need_vpn", "status", "data_center"], response.data["results"][0])


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

    def apply_response_data_keys_assert(self, data):
        self.assertKeysIn(["id", "private_ip", "public_ip", "vcpu",
                           "ram", "disk_size", "duration_days", "company",
                           "contact", "purpose", "creation_time", "status",
                           "service"], data)

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

    def test_admin_list_apply(self):
        response = response = self.create_apply()
        self.assertEqual(response.status_code, 201)
        apply_id = response.data['id']

        url = reverse('api:apply-quota-admin-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 0)

        self.service.users.add(self.user)  # 加管理权限

        url = reverse('api:apply-quota-admin-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data["count"], 1)
        self.apply_response_data_keys_assert(response.data['results'][0])
        self.assertEqual(response.data['results'][0]['status'], 'wait')
