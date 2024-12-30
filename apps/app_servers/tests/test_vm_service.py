from urllib import parse

from django.urls import reverse
from utils.test import get_or_create_user, get_or_create_service, MyAPITransactionTestCase, MyAPITestCase

from apps.app_servers.models import ServiceConfig
from apps.app_servers.managers import ServicePrivateQuotaManager, ServiceShareQuotaManager
from apps.service.models import OrgDataCenterAdminUser


class VmServiceQuotaTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(user=self.user)
        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='service2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False
        )
        self.service2.save(force_insert=True)

    def test_list_service_private_quota(self):
        url = reverse('servers-api:vms-service-p-quota-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # service private quota create
        ServicePrivateQuotaManager().get_quota(service=self.service)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(keys=[
            "private_ip_total", "public_ip_total", "vcpu_total",
            "ram_total", "disk_size_total", "private_ip_used",
            "public_ip_used", "vcpu_used", "ram_used",
            "disk_size_used", "creation_time", "enable", "service"
        ], container=response.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=response.data['results'][0]['service'])
        self.assertEqual(response.data['results'][0]['service']['id'], self.service.id)

        # service2 private quota create
        ServicePrivateQuotaManager().get_quota(service=self.service2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        # service deleted
        self.service.status = self.service.Status.DELETED.value
        self.service.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)

        # service2 disable
        self.service2.status = self.service.Status.DISABLE.value
        self.service2.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)

        # param 'service_id'
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'service_id': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'service_id': self.service2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)

        # service enable
        self.service.status = self.service.Status.ENABLE.value
        self.service.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        ServicePrivateQuotaManager().increase(service=self.service2, ram_gib=2)
        ServicePrivateQuotaManager().deduct(service=self.service2, ram_gib=1)
        query = parse.urlencode(query={'service_id': self.service2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ram_total'], 2)
        self.assertEqual(response.data['results'][0]['ram_used'], 1)

        self._param_data_center_id_test(url=url)

    def _param_data_center_id_test(self, url: str):
        # data_center_id
        query = parse.urlencode(query={'data_center_id': self.service.org_data_center.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'data_center_id': 'xx'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={
            'data_center_id': self.service.org_data_center.organization_id, 'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_service_share_quota(self):
        url = reverse('servers-api:vms-service-s-quota-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # service share quota create
        ServiceShareQuotaManager().get_quota(service=self.service)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(keys=[
            "private_ip_total", "public_ip_total", "vcpu_total",
            "ram_total", "disk_size_total", "private_ip_used",
            "public_ip_used", "vcpu_used", "ram_used",
            "disk_size_used", "creation_time", "enable", "service"
        ], container=response.data['results'][0])
        self.assertEqual(response.data['results'][0]['service']['id'], self.service.id)
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=response.data['results'][0]['service'])

        # service2 share quota create
        ServiceShareQuotaManager().get_quota(service=self.service2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        # service deleted
        self.service.status = self.service.Status.DELETED.value
        self.service.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)
        self.assertEqual(len(response.data['results']), 1)

        # service2 disable
        self.service2.status = self.service.Status.DISABLE.value
        self.service2.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)
        self.assertEqual(len(response.data['results']), 1)

        # param 'service_id'
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'service_id': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        self.assertEqual(response.data['count'], 0)

        query = parse.urlencode(query={'service_id': self.service2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['service']['id'], self.service2.id)
        self.assertEqual(len(response.data['results']), 1)

        # service enable
        self.service.status = self.service.Status.ENABLE.value
        self.service.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)

        ServiceShareQuotaManager().increase(service=self.service2, ram_gib=4)
        ServiceShareQuotaManager().deduct(service=self.service2, ram_gib=3)
        query = parse.urlencode(query={'service_id': self.service2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ram_total'], 4)
        self.assertEqual(response.data['results'][0]['ram_used'], 3)

        # data_center_id
        self._param_data_center_id_test(url=url)


class ServiceTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(user=self.user)
        self.service = get_or_create_service()

    def test_list_service(self):
        service2 = ServiceConfig(name='service2', name_en='service2 en')
        service2.save(force_insert=True)

        url = reverse('servers-api:service-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertKeysIn(["id", "name", "name_en", "service_type", "cloud_type", "add_time", "sort_weight",
                           "need_vpn", "status", "org_data_center", 'longitude', 'latitude', 'pay_app_service_id',
                           'disk_available', 'only_admin_visible', 'version', 'version_update_time', 'endpoint_url'
                           ], response.data["results"][0])
        self.assertEqual(len(response.data["results"]), 2)
        map_ = {s['id']: s for s in response.data["results"]}
        r_service1 = map_[self.service.id]
        r_service2 = map_[service2.id]
        self.assertKeysIn([
            "id", "name", "name_en", "sort_weight", "organization"], r_service1['org_data_center'])
        self.assertKeysIn(["id", "name", "name_en", "sort_weight"], r_service1['org_data_center']['organization'])
        self.assertIsInstance(r_service1['status'], str)
        self.assertEqual(r_service1['status'], ServiceConfig.Status.ENABLE)
        self.assertIs(r_service1['disk_available'], False)
        self.assertIsNone(r_service2['org_data_center'])

        url = reverse('servers-api:service-list')
        query = parse.urlencode(query={'center_id': self.service.org_data_center_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        url = reverse('servers-api:service-list')
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
        url = reverse('servers-api:service-list')
        query = parse.urlencode(query={'status': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidStatus', response=response)

        # param 'status'
        url = reverse('servers-api:service-list')
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

        # as-admin
        service2.status = ServiceConfig.Status.ENABLE.value
        service2.save(update_fields=['status'])

        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        service2.users.add(self.user)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertNotIn('admin_users', response.data["results"][0])

        query = parse.urlencode(query={'as-admin': '', 'with_admin_users': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertIn('admin_users', response.data["results"][0])
        self.assertKeysIn(["id", "username", "role"], response.data["results"][0]['admin_users'][0])
        self.assertEqual(len(response.data["results"][0]['admin_users']), 1)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['id'], self.user.id)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['username'], self.user.username)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['role'], OrgDataCenterAdminUser.Role.ADMIN.value)

        # 同为数据中心运维和服务单元管理员
        service2.org_data_center = self.service.org_data_center
        service2.save(update_fields=['org_data_center'])
        self.service.org_data_center.add_admin_user(self.user, is_ops_user=True)
        query = parse.urlencode(query={'as-admin': '', 'with_admin_users': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        sv_map = {s['id']: s for s in response.data["results"]}
        r_service1 = sv_map[self.service.id]
        r_service2 = sv_map[service2.id]
        # service2
        self.assertEqual(len(r_service2['admin_users']), 2)
        self.assertEqual(r_service2['admin_users'][0]['id'], self.user.id)
        self.assertEqual(r_service2['admin_users'][0]['username'], self.user.username)
        self.assertEqual(r_service2['admin_users'][0]['role'], OrgDataCenterAdminUser.Role.ADMIN.value)
        self.assertEqual(r_service2['admin_users'][1]['id'], self.user.id)
        self.assertEqual(r_service2['admin_users'][1]['username'], self.user.username)
        self.assertEqual(r_service2['admin_users'][1]['role'], OrgDataCenterAdminUser.Role.OPS.value)
        # service1
        self.assertEqual(len(r_service1['admin_users']), 1)
        self.assertEqual(r_service1['admin_users'][0]['id'], self.user.id)
        self.assertEqual(r_service1['admin_users'][0]['username'], self.user.username)
        self.assertEqual(r_service1['admin_users'][0]['role'], OrgDataCenterAdminUser.Role.OPS.value)

    def test_admin_list(self):
        service2 = ServiceConfig(name='service2', name_en='service2 en', org_data_center=None)
        service2.save(force_insert=True)

        url = reverse('servers-api:service-admin-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data['count'], 0)

        self.service.users.add(self.user)
        query = parse.urlencode(query={'with_admin_users': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertKeysIn(["id", "name", "name_en", "service_type", "cloud_type", "add_time", "sort_weight",
                           "need_vpn", "status", "org_data_center", 'longitude', 'latitude', 'pay_app_service_id',
                           'disk_available', 'only_admin_visible', 'version', 'version_update_time', 'admin_users',
                           'endpoint_url'
                           ], response.data["results"][0])
        self.assertKeysIn([
            "id", "name", "name_en", "sort_weight", "organization"], response.data["results"][0]['org_data_center'])
        self.assertKeysIn(["id", "name", "name_en", "sort_weight"
                           ], response.data["results"][0]['org_data_center']['organization'])
        self.assertIsInstance(response.data["results"][0]['status'], str)
        self.assertEqual(len(response.data["results"][0]['admin_users']), 1)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['id'], self.user.id)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['username'], self.user.username)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['role'], OrgDataCenterAdminUser.Role.ADMIN.value)

        # 数据中心管理员
        self.service.users.remove(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        self.service.org_data_center.add_admin_user(user=self.user, is_ops_user=True)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertNotIn('admin_users', response.data["results"][0])

        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data["results"][0]['admin_users']), 1)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['id'], self.user.id)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['username'], self.user.username)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['role'], OrgDataCenterAdminUser.Role.OPS.value)

        # 同为数据中心运维和服务单元管理员
        self.service.users.add(self.user)
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data["results"][0]['admin_users']), 2)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['id'], self.user.id)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['username'], self.user.username)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['role'], OrgDataCenterAdminUser.Role.ADMIN.value)
        self.assertEqual(response.data["results"][0]['admin_users'][1]['id'], self.user.id)
        self.assertEqual(response.data["results"][0]['admin_users'][1]['username'], self.user.username)
        self.assertEqual(response.data["results"][0]['admin_users'][1]['role'], OrgDataCenterAdminUser.Role.OPS.value)

        # 同为数据中心和服务单元管理员
        self.service.org_data_center.add_admin_user(user=self.user, is_ops_user=False)
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data["results"][0]['admin_users']), 1)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['id'], self.user.id)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['username'], self.user.username)
        self.assertEqual(response.data["results"][0]['admin_users'][0]['role'], OrgDataCenterAdminUser.Role.ADMIN.value)

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
        url = reverse('servers-api:service-private-quota', kwargs={'id': self.service.id})
        self.service_quota_get_update(url=url)

    def test_share_quota(self):
        url = reverse('servers-api:service-share-quota', kwargs={'id': self.service.id})
        self.service_quota_get_update(url=url)

    def test_version(self):
        service2 = ServiceConfig(
            name='service2', name_en='service2 en', org_data_center=self.service.org_data_center,
            username='test'
        )
        service2.set_password(raw_password='test')
        service2.save(force_insert=True)

        url = reverse('servers-api:service-version', kwargs={'id': self.service.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["version", "version_update_time"], response.data)

        url = reverse('servers-api:service-version', kwargs={'id': service2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
