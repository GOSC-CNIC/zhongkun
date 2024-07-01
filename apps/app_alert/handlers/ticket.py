from apps.app_alert.models import AlertService
from apps.app_alert.models import AlertModel
from apps.app_alert.models import AlertAbstractModel
from apps.app_alert.models import ServiceLog
from apps.app_alert.models import ServiceMetric
from apps.app_alert.utils import errors


def has_service_permission(service_name, user):
    if user.is_superuser:
        return True
    service = AlertService.objects.filter(name_en=service_name).first()
    if not service:
        raise errors.InvalidArgument('invalid service')

    service_user = service.users.filter(username=user.username)
    if service_user:
        return True


class ServerAdapter(object):
    def __init__(self, alerts):
        self.alerts = alerts

    def get_service_set(self):
        service_set = set()
        for cluster in self.get_cluster_set():
            service = self.search_cluster_service(cluster=cluster)
            service_set.add(service)
        return service_set

    def get_cluster_set(self):
        cluster_set = set()
        for alert_id in self.alerts:
            alert_obj = AlertModel.objects.filter(id=alert_id).first()
            if not alert_obj:
                continue
            if alert_obj.cluster == AlertAbstractModel.AlertType.WEBMONITOR.value:
                continue
            cluster_set.add(alert_obj.cluster)
        return cluster_set

    @staticmethod
    def search_cluster_service(cluster):
        service_log_obj = ServiceLog.objects.filter(job_tag=cluster).first()
        if service_log_obj:
            return service_log_obj.service
        service_metric_obj = ServiceMetric.objects.filter(job_tag=cluster).first()
        if service_metric_obj:
            return service_metric_obj.service
        return None
