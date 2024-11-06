from typing import List
from datetime import timedelta

from django.utils import timezone as dj_timezone
from django.db.models import Q

from core import errors
from core import taskqueue
from core.request import request_service
from apps.servers.models import ServiceConfig, Server


def task_update_service_server_count(services: List[ServiceConfig]):
    for service in services:
        if service.service_type in [ServiceConfig.ServiceType.EVCLOUD.value, ServiceConfig.ServiceType.OPENSTACK.value]:
            try:
                r = request_service(service=service, method='resource_statistics')
            except errors.Error as exc:
                continue

            service.server_total = r.server_count
            service.server_managed = Server.objects.filter(service_id=service.id).count()
            service.server_update_time = dj_timezone.now()
            service.save(update_fields=['server_total', 'server_managed', 'server_update_time'])


def update_services_server_count(service: ServiceConfig = None, update_ago_minutes: int = 5):
    """
    :update_ago_minutes: >=0有效，更新时间在指定分钟数之前的所有服务单元也尝试更新
    """
    if service:
        all_services = [service]
    else:
        all_services = []

    if update_ago_minutes >= 0:
        try:
            ago_time = dj_timezone.now() - timedelta(minutes=update_ago_minutes)
            qs = ServiceConfig.objects.filter(
                status=ServiceConfig.Status.ENABLE.value
            ).filter(
                Q(server_update_time__isnull=True) | Q(server_update_time__lt=ago_time)
            )
            # 排除
            if service:
                qs = qs.exclude(id=service.id)

            services = list(qs)
            all_services += services
        except Exception as exc:
            pass

    if all_services:
        taskqueue.submit_task(task_update_service_server_count, kwargs={'services': all_services})
