from django.contrib.auth import get_user_model

from service.models import DataCenter, ServiceConfig


User = get_user_model()


def get_or_create_user(username='test', password='password'):
    user, created = User.objects.get_or_create(username=username, password=password)
    return user


def get_or_create_service():
    service = ServiceConfig.objects.filter(name='test').first()
    if service is None:
        center = DataCenter(name='test')
        center.save()

        service = ServiceConfig(name='test', data_center=center, endpoint_url='test', username='', password='')
        service.save()

    return service

