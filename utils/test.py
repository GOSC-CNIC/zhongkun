from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.test import APITestCase, APITransactionTestCase

from service.models import DataCenter, ServiceConfig
from users.models import UserProfile
from storage.models import ObjectsService


User = get_user_model()


def get_test_case_settings():
    test_settings = getattr(settings, 'TEST_CASE', None)
    if test_settings is None:
        raise Exception('No test settings(TEST_CASE) in file "test_settings.py", '
                        'Check whether it is in debug mode(Debug=True)')

    return test_settings


def get_or_create_user(username='test', password='password', company: str = 'cnic') -> UserProfile:
    user, created = User.objects.get_or_create(username=username, password=password, company=company, is_active=True)
    return user


def get_or_create_center(name='test'):
    center = DataCenter.objects.filter(name=name, name_en='test_en').first()
    if center is None:
        center = DataCenter(name='test', name_en='test_en')
        center.save(force_insert=True)

    return center


def get_or_create_organization(name: str):
    return get_or_create_center(name)


def get_or_create_service():
    service = ServiceConfig.objects.filter(name='test', name_en='test_en').first()
    if service is None:
        center = get_or_create_center()

        test_settings = get_test_case_settings()
        service_settings = test_settings['SERVICE']

        service_type = 'evcloud'
        if 'service_type' in service_settings:
            service_type = service_settings['service_type']

        if service_type not in ServiceConfig.ServiceType.values:
            raise Exception('TEST_CASE.SERVICE.service_type is invalid in settings')

        cloud_type = 'private'
        if 'cloud_type' in service_settings:
            cloud_type = service_settings['cloud_type']

        cloud_type = cloud_type.lower()
        if cloud_type not in ServiceConfig.CLoudType.values:
            raise Exception('TEST_CASE.SERVICE.cloud_type is invalid in settings')

        service = ServiceConfig(
            name='test', name_en='test_en', data_center=center,
            endpoint_url=service_settings['endpoint_url'],
            username=service_settings['username'],
            service_type=service_type,
            cloud_type=cloud_type,
            region_id=service_settings['region_id']
        )
        service.set_password(service_settings['password'])
        service.save()

    return service


def get_or_create_storage_service():
    service = ObjectsService.objects.filter(name='test', name_en='test_en').first()
    if service is None:
        center = get_or_create_center()

        test_settings = get_test_case_settings()
        service_settings = test_settings['STORAGE_SERVICE']

        service_type = 'iharbor'
        if 'service_type' in service_settings:
            service_type = service_settings['service_type']

        if service_type not in ObjectsService.ServiceType.values:
            raise Exception('TEST_CASE.STORAGE_SERVICE.service_type is invalid in settings')

        service = ObjectsService(
            name='test', name_en='test_en', data_center=center,
            endpoint_url=service_settings['endpoint_url'],
            username=service_settings['username'],
            service_type=service_type,
            api_version=service_settings['version']
        )
        service.set_password(service_settings['password'])
        service.save()

    return service


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
                self.fail(f'{sub} is not sub dict of {d}, Not Equal key is {k}, {v} != {d.get(k)}')

        return True


class MyAPITransactionTestCase(APITransactionTestCase):
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
                self.fail(f'{sub} is not sub dict of {d}, Not Equal key is {k}, {v} != {d.get(k)}')

        return True
