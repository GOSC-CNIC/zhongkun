import json
import re
import datetime
from apps.app_alert.utils.utils import hash_sha1
from django.forms.models import model_to_dict
from django.db.models import Count
from apps.app_alert.utils.errors import BadRequest
from apps.app_alert.utils.utils import download
from django.db.utils import IntegrityError
from apps.app_alert.models import PreAlertModel
from apps.app_alert.models import AlertModel
from apps.app_alert.models import ResolvedAlertModel
from apps.app_alert.models import AlertLifetimeModel
from apps.app_alert.models import AlertWorkOrder
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.contrib.contenttypes.models import ContentType
from apps.app_alert.utils.utils import DateUtils


class AlertReceiver(object):
    AIOPS_BACKEND_CONFIG = settings.AIOPS_BACKEND_CONFIG

    def __init__(self, data):
        self.timestamp = DateUtils.timestamp()
        self.data = data
        self.need_to_pretreatment_type = ["webmonitor"]  # 网站类需要预处理
        self.fingerprint_field = "fingerprint"

    def start(self):
        pool = ThreadPoolExecutor(max_workers=1)
        pool.submit(self._start, )
        pool.shutdown(wait=False)

    def _start(self):
        items = self.clean()
        prepare_alerts, alerts = self.group_by_prepare_type(items)
        self.create_or_update(PreAlertModel, prepare_alerts)
        alerts.extend(self.pick_inaccessible_website_list())
        self.create_or_update(AlertModel, alerts, save_lifetime=True)
        self.firing_to_resolved()
        self.update_alert_lifetime()

    def clean(self):
        items = []
        for alert in self.data:
            fingerprint = self.generate_fingerprint(alert)
            annotations = alert.get("annotations")
            labels = alert.get("labels")
            cluster, alert_type = self.parse_alert_type_field(alert)
            instance = self.parse_alert_instance(alert_type=alert_type, alert=alert)
            severity = labels.get("severity") or "warning"
            item = dict()
            item[self.fingerprint_field] = fingerprint
            item["name"] = labels.get("alertname")
            item["type"] = alert_type
            item["instance"] = instance
            item["port"] = ""
            item["cluster"] = cluster
            item["severity"] = severity
            item["summary"] = annotations.get("summary")
            item["description"] = annotations.get("description")
            item["start"] = self.date_to_timestamp(alert.get("startsAt"))
            item["end"] = self.generate_alert_end_timestamp(alert, cluster)
            items.append(item)
        return items

    @staticmethod
    def generate_fingerprint(alert):
        """
        计算 fingerprint：
            hash(annotations.summary + labels)
        """
        annotations = alert.get("annotations")
        summary = annotations.get("summary")
        labels = alert.get("labels")
        labels.pop("device", "")
        _str = json.dumps(summary) + json.dumps(labels)
        return hash_sha1(_str)

    @staticmethod
    def parse_alert_type_field(alert):
        """
        根据 monitor_cluster判断，是网站类、指标类、日志类
        """
        labels = alert.get("labels")
        cluster = labels.get("monitor_cluster") or labels.get("job") or ""  # 告警集群名称
        cluster = cluster.lower()
        if "webmonitor" in cluster:
            alert_type = "webmonitor"
        elif cluster.endswith("_log"):
            alert_type = "log"
        elif cluster.endswith("_metric"):
            alert_type = "metric"
        else:
            raise BadRequest(detail=f"invalid cluster:`{cluster}`,\n\n{json.dumps(alert)}")
        return cluster, alert_type

    def parse_alert_instance(self, alert_type, alert):
        """
        解析 instance 字段
        """
        if alert_type == 'metric':
            instance = alert.get("labels").get("instance")
        elif alert_type == 'log':
            annotations = alert.get("annotations")
            description = annotations.get("description")
            log_name = re.findall(r'{"name":"(.*?)"}', description)
            instance = log_name[0] if log_name else ""
        else:
            instance = ""

        return instance

    @staticmethod
    def date_to_timestamp(date_string):
        date = date_string.split(".")[0]
        date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
        ts = DateUtils.date_to_ts(dt=date, fmt="%Y-%m-%dT%H:%M:%S")
        return ts

    def generate_alert_end_timestamp(self, alert, cluster):
        """
        生成预结束时间
        """
        if cluster in ["mail_metric", "mail_log"]:
            return self.timestamp + 60 * 5
        recent_alerts = ResolvedAlertModel.objects.filter(
            fingerprint=alert.get("fingerprint"),
            start__gte=self.timestamp - 86400,
            start__lte=self.timestamp)
        if recent_alerts and len(recent_alerts) >= 10:
            return self.timestamp + 60 * 60 * 3
        return self.timestamp + 60 * 60

    def group_by_prepare_type(self, items):
        """
        判断是不是预处理网站类
        """
        prepare_alerts = []
        alerts = []
        for item in items:
            if item.get("type") in self.need_to_pretreatment_type:
                prepare_alerts.append(item)
            else:
                alerts.append(item)
        return prepare_alerts, alerts

    def create_or_update(self, model, items, save_lifetime=False):
        for item in items:
            existed_obj = model.objects.filter(fingerprint=item.get(self.fingerprint_field)).first()
            if existed_obj:
                existed_obj.end = item.get("end")
                existed_obj.description = item.get("description")
                existed_obj.modification = self.timestamp
                existed_obj.count = existed_obj.count + 1
                existed_obj.save()
                continue
            item["creation"] = item["modification"] = self.timestamp
            alert = model.objects.create(**item)
            if save_lifetime:
                alert_lifetime = {
                    "id": alert.id,
                    "start": item.get("start"),
                    "status": AlertLifetimeModel.Status.FIRING.value}
                AlertLifetimeModel.objects.create(**alert_lifetime)

    @staticmethod
    def get_probe_count():
        probe_model = ContentType.objects.get(app_label="monitor", model="websitedetectionpoint").model_class()
        count = probe_model.objects.filter(enable=True).count() or 2
        return 2  # TODO

    def pick_inaccessible_website_list(self):
        """
        从预处理表中挑选出所有探针都为异常的网站
        """
        alerts = []
        probe_count = self.get_probe_count()
        results = PreAlertModel.objects.filter(end__gte=self.timestamp).values("summary").annotate(
            count=Count('summary'))
        for item in results:
            summary = item.get("summary")
            count = item.get("count")
            if count != probe_count:
                continue
            website_alert = self.init_website_alert(summary)
            alerts.append(website_alert)
        return alerts

    def init_website_alert(self, item):
        pop_keys = ["id", "count", "first_notification", "last_notification", "creation", "modification"]
        obj = PreAlertModel.objects.filter(summary=item).first()
        website_alert = model_to_dict(obj)
        for key in pop_keys:
            website_alert.pop(key, "")
        description = website_alert["description"].split()
        url_hash = description[-2]
        website_alert["cluster"] = "webMonitor"
        website_alert["description"] = " ".join(description[:-2])
        website_alert["start"] = self.timestamp
        website_alert[self.fingerprint_field] = url_hash
        return website_alert

    def firing_to_resolved(self):
        """
        当告警end字段小于当前时间时,归入已恢复队列

            日志类的需要创建工单后，才会移入已恢复队列
        """
        # 进行中告警中 挑选出 end 小于当前时间的告警
        alerts = AlertModel.objects.filter(end__lt=self.timestamp).all()
        for alert in alerts:
            # 非log告警, 移入 resolved
            if alert.type != 'log':
                self.move_to_resolved(alert)
                # log告警创建工单后会归入resolved
            elif AlertWorkOrder.objects.filter(alert_id=alert.id).first():
                self.move_to_resolved(alert)

    def move_to_resolved(self, alert):
        item = model_to_dict(alert)
        item["id"] = alert.id
        item["modification"] = self.timestamp
        try:
            ResolvedAlertModel.objects.create(**item)
        except IntegrityError as e:
            pass
        alert.delete()

    @staticmethod
    def update_alert_lifetime():
        """
        更新告警生命周期
        """
        # 挑选出 end 为空的告警
        firing_alerts = AlertLifetimeModel.objects.filter(end__isnull=True)
        for alert in firing_alerts:
            order = AlertWorkOrder.objects.filter(alert_id=alert.id).first()
            if order:
                alert.end = order.creation
                alert.status = AlertLifetimeModel.Status.WORK_ORDER.value
                alert.save()
                continue
            resolved = ResolvedAlertModel.objects.filter(id=alert.id).first()
            if resolved:
                alert.end = resolved.end
                alert.status = AlertLifetimeModel.Status.RESOLVED.value
                alert.save()
