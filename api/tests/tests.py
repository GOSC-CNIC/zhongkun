import hashlib
import collections
import io
import random
from string import printable
from urllib import parse
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from utils.model import PayType, OwnerType

from service.models import (
    ApplyOrganization, DataCenter, ApplyVmService, ServiceConfig
)
from utils.test import get_or_create_user, get_or_create_service, get_or_create_center

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
        self.assertKeysIn(["id", "name", "sort_weight", "creation_time", "status", "desc", 'longitude', 'latitude'],
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


class ApplyOrganizationTests:   # (MyAPITestCase):
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


class ApplyVmServiceTests:  # (MyAPITestCase):
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
