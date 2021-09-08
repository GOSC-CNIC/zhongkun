from django.test import TestCase

from utils.test import get_test_case_settings, get_or_create_service
from .models import MonitorProvider, MonitorJobCeph


def get_or_create_monitor_provider(name: str = 'test', name_en: str = 'test'):
    provider = MonitorProvider.objects.filter(name=name).first()
    if provider is not None:
        return provider

    try:
        test_settings = get_test_case_settings()
        provider_settings = test_settings['MONITOR_CEPH']['PROVIDER']
    except Exception as e:
        raise Exception(f'No test settings(MONITOR_CEPH.PROVIDER) in file "test_settings.TEST_CASE"， {str(e)}')

    provider = MonitorProvider(
        name=name, name_en=name_en,
        endpoint_url=provider_settings.get('endpoint_url'),
        username=provider_settings.get('username')
    )
    provider.set_password(provider_settings.get('password', ''))
    provider.save()
    return provider


def get_or_create_monitor_job_ceph(service_id: str, job_tag: str = None, name: str = 'test', name_en: str = 'test'):
    if job_tag is None:
        try:
            test_settings = get_test_case_settings()
            job_settings = test_settings['MONITOR_CEPH']['JOB_CEPH']
        except Exception as e:
            raise Exception(f'No test settings(MONITOR_CEPH.JOB_CEPH) in file "test_settings.TEST_CASE"， {str(e)}')

        job_tag = job_settings['job_tag']

    if not job_tag:
        raise Exception('invalid "job_tag"')

    job_ceph = MonitorJobCeph.objects.filter(service_id=service_id, job_tag=job_tag).first()
    if job_ceph is not None:
        return job_ceph

    provider = get_or_create_monitor_provider()
    job_ceph = MonitorJobCeph(
        name=name, name_en=name_en, job_tag=job_tag,
        provider=provider, service_id=service_id
    )
    job_ceph.save()
    return job_ceph
