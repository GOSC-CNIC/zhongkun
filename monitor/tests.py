from utils.test import get_test_case_settings
from .models import MonitorProvider, MonitorJobCeph, MonitorJobServer, MonitorJobVideoMeeting


def get_or_create_monitor_provider(alias: str, name: str = 'test', name_en: str = 'test'):
    provider = MonitorProvider.objects.filter(name=name).first()
    if provider is not None:
        return provider

    try:
        test_settings = get_test_case_settings()
        provider_settings = test_settings[alias]['PROVIDER']
    except Exception as e:
        raise Exception(f'No test settings({alias}.PROVIDER) in file "test_settings.TEST_CASE"， {str(e)}')

    provider = MonitorProvider(
        name=name, name_en=name_en,
        endpoint_url=provider_settings.get('endpoint_url'),
        username=provider_settings.get('username')
    )
    provider.set_password(provider_settings.get('password', ''))
    provider.save()
    return provider


def get_or_create_monitor_job_ceph(job_tag: str = None, name: str = 'test', name_en: str = 'test'):
    if job_tag is None:
        try:
            test_settings = get_test_case_settings()
            job_settings = test_settings['MONITOR_CEPH']['JOB_CEPH']
        except Exception as e:
            raise Exception(f'No test settings(MONITOR_CEPH.JOB_CEPH) in file "test_settings.TEST_CASE"， {str(e)}')

        job_tag = job_settings['job_tag']

    if not job_tag:
        raise Exception('invalid "job_tag"')

    job_ceph = MonitorJobCeph.objects.filter(job_tag=job_tag).first()
    if job_ceph is not None:
        return job_ceph

    provider = get_or_create_monitor_provider(alias='MONITOR_CEPH')
    job_ceph = MonitorJobCeph(
        name=name, name_en=name_en, job_tag=job_tag,
        provider=provider
    )
    job_ceph.save()
    return job_ceph


def get_or_create_monitor_job_server(job_tag: str = None, name: str = 'test', name_en: str = 'test'):
    if job_tag is None:
        try:
            test_settings = get_test_case_settings()
            job_settings = test_settings['MONITOR_SERVER']['JOB_SERVER']
        except Exception as e:
            raise Exception(f'No test settings(MONITOR_SERVER.JOB_SERVER) in file "test_settings.TEST_CASE"， {str(e)}')

        job_tag = job_settings['job_tag']

    if not job_tag:
        raise Exception('invalid "job_tag"')

    job_server = MonitorJobServer.objects.filter(job_tag=job_tag).first()
    if job_server is not None:
        return job_server

    provider = get_or_create_monitor_provider(alias='MONITOR_SERVER')
    job_server = MonitorJobServer(
        name=name, name_en=name_en, job_tag=job_tag,
        provider=provider
    )
    job_server.save()
    return job_server


def get_or_create_monitor_job_meeting(job_tag: str = None, name: str = 'test', name_en: str = 'test'):
    if job_tag is None:
        try:
            test_settings = get_test_case_settings()
            job_settings = test_settings['MONITOR_VIDEO_MEETING']['JOB_MEETING']
        except Exception as e:
            raise Exception(f'No test settings(MONITOR_VIDEO_MEETING.JOB_MEETING) in '
                            f'file "test_settings.TEST_CASE"， {str(e)}')

        job_tag = job_settings['job_tag']

    if not job_tag:
        raise Exception('invalid "job_tag"')

    job_meeting = MonitorJobVideoMeeting.objects.filter(job_tag=job_tag).first()
    if job_meeting is not None:
        return job_meeting

    provider = get_or_create_monitor_provider(alias='MONITOR_VIDEO_MEETING')
    job_meeting = MonitorJobVideoMeeting(
        name=name, name_en=name_en, job_tag=job_tag,
        provider=provider, ips='10.0.0.1; 10.10.10.2',
        longitude=33, latitude=66
    )
    job_meeting.save()
    return job_meeting
