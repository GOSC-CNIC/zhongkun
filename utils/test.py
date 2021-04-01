from django.contrib.auth import get_user_model
from django.conf import settings

from service.models import DataCenter, ServiceConfig


User = get_user_model()


def get_or_create_user(username='test', password='password'):
    user, created = User.objects.get_or_create(username=username, password=password, is_active=True)
    return user


def get_or_create_center():
    center = DataCenter.objects.filter(name='test').first()
    if center is None:
        center = DataCenter(name='test')
        center.save()

    return center


def get_or_create_service():
    service = ServiceConfig.objects.filter(name='test').first()
    if service is None:
        center = get_or_create_center()

        test_settings = getattr(settings, 'TEST_CASE')
        service_settings = test_settings['SERVICE']
        s_type_str = getattr(service_settings, 'service_type', 'evcloud').lower()
        service_type = [k for k, v in ServiceConfig.SERVICE_TYPE_STRING.items() if v == s_type_str][0]
        service = ServiceConfig(
            name='test', data_center=center,
            endpoint_url=service_settings['endpoint_url'],
            username=service_settings['username'],
            password=service_settings['password'],
            service_type=service_type,
            region_id=service_settings['region_id'],
        )
        service.save()

    return service

