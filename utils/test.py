from django.contrib.auth import get_user_model
from django.conf import settings

from service.models import DataCenter, ServiceConfig
from users.models import UserProfile


User = get_user_model()


def get_test_case_settings():
    test_settings = getattr(settings, 'TEST_CASE', None)
    if test_settings is None:
        raise Exception('No test settings(TEST_CASE) in file "test_settings.py", '
                        'Check whether it is in debug mode(Debug=True)')

    return test_settings


def get_or_create_user(username='test', password='password') -> UserProfile:
    user, created = User.objects.get_or_create(username=username, password=password, is_active=True)
    return user


def get_or_create_center():
    center = DataCenter.objects.filter(name='test', name_en='test_en').first()
    if center is None:
        center = DataCenter(name='test', name_en='test_en')
        center.save()

    return center


def get_or_create_service():
    service = ServiceConfig.objects.filter(name='test', name_en='test_en').first()
    if service is None:
        center = get_or_create_center()

        test_settings = get_test_case_settings()
        service_settings = test_settings['SERVICE']
        s_type_str = getattr(service_settings, 'service_type', 'evcloud').lower()
        if s_type_str == 'evcloud':
            service_type = ServiceConfig.ServiceType.EVCLOUD
        elif s_type_str == 'openstack':
            service_type = ServiceConfig.ServiceType.OPENSTACK
        elif s_type_str == 'vmware':
            service_type = ServiceConfig.ServiceType.VMWARE
        else:
            raise Exception('TEST_CASE.SERVICE.service_type is invalid in settings')

        service = ServiceConfig(
            name='test', name_en='test_en', data_center=center,
            endpoint_url=service_settings['endpoint_url'],
            username=service_settings['username'],
            service_type=service_type,
            region_id=service_settings['region_id']
        )
        service.set_password(service_settings['password'])
        service.save()

    return service

