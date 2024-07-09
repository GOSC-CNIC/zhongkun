from apps.app_alert.models import AlertModel
from apps.app_alert.models import ResolvedAlertModel
from apps.app_alert.utils.utils import DateUtils
from django.forms.models import model_to_dict
from django.db import transaction


class AlertStatusFlow(object):
    def __init__(self):
        pass

    @classmethod
    def start(cls):
        """
        遍历所有进行中的告警，当预结束时间小于当前时间时，归入已恢复队列
        """
        alert_list = AlertModel.objects.filter(end__lt=DateUtils.timestamp())
        for alert in alert_list:
            cls.move_to_resolved(alert)

    @staticmethod
    def move_to_resolved(obj):
        item = model_to_dict(obj)
        item["id"] = obj.id
        item['status'] = AlertModel.AlertStatus.RESOLVED.value
        item["modification"] = item["recovery"] = DateUtils.timestamp()
        with transaction.atomic():
            ResolvedAlertModel.objects.create(**item)
            obj.delete()
