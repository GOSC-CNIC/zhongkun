import json
import re
import datetime
from apps.app_alert.utils.utils import hash_sha1
from django.db.models import Count
from apps.app_alert.utils.errors import BadRequest
from apps.app_alert.models import PreAlertModel
from apps.app_alert.models import AlertModel
from apps.app_alert.utils.utils import DateUtils
from django.utils import timezone
from apps.app_alert.alert_status_flow import AlertStatusFlow
from apps.monitor.models import WebsiteDetectionPoint


class AlertReceiver(object):

    def __init__(self, data):
        self.timestamp = DateUtils.timestamp()
        self.data = data
        self.need_to_pretreatment_type = [AlertModel.AlertType.WEBMONITOR.value]  # 网站类需要预处理
        self.fingerprint_field = "fingerprint"

    def start(self):
        items = self.clean()
        prepare_alerts, alerts = self.group_by_prepare_type(items)
        self.create_or_update(PreAlertModel, prepare_alerts)
        alerts.extend(self.pick_inaccessible_website_list())
        self.create_or_update(AlertModel, alerts)
        # 告警状态流转处理
        AlertStatusFlow.start()

    def clean(self):
        items = []
        for alert in self.data:
            fingerprint = self.generate_fingerprint(alert)
            annotations = alert.get("annotations")
            labels = alert.get("labels")
            cluster, alert_type = self.parse_alert_type_field(alert)
            instance = self.parse_alert_instance(alert_type=alert_type, alert=alert)
            severity = labels.get("severity") or AlertModel.AlertSeverity.WARNING.value
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
            item["end"] = self.generate_alert_end_timestamp()
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
        if AlertModel.AlertType.WEBMONITOR.value in cluster:
            alert_type = AlertModel.AlertType.WEBMONITOR.value
        elif cluster.endswith(AlertModel.AlertType.LOG.value):
            alert_type = AlertModel.AlertType.LOG.value
        elif cluster.endswith(AlertModel.AlertType.METRIC.value):
            alert_type = AlertModel.AlertType.METRIC.value
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

    def generate_alert_end_timestamp(self):
        """
        生成预结束时间
        """
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

    def create_or_update(self, model, items):
        for item in items:
            existed_obj = model.objects.filter(fingerprint=item.get(self.fingerprint_field)).first()
            if existed_obj:  # 如果存在则更新end description modification count字段
                existed_obj.end = item.get("end")
                existed_obj.description = item.get("description")
                existed_obj.modification = self.timestamp
                existed_obj.count = existed_obj.count + 1
                existed_obj.save()
                continue
            timestamp = timezone.now().timestamp()
            item["creation"] = timestamp
            item["modification"] = int(timestamp)
            model.objects.create(**item)

    @staticmethod
    def get_probe_count():
        point_count = WebsiteDetectionPoint.objects.filter(enable=True).count()
        if point_count > 1:
            return 2  # TODO
        else:
            return 1

    def pick_inaccessible_website_list(self):
        """
        从预处理表中挑选出所有探针都为异常的网站
        """
        alerts = []
        results = PreAlertModel.objects.filter(end__gte=self.timestamp).values("summary").annotate(
            count=Count('summary'))
        for item in results:
            summary = item.get("summary")
            count = item.get("count")
            if count != self.get_probe_count():
                continue
            website_alert = self.generate_website_alert(summary)
            alerts.append(website_alert)
        return alerts

    def generate_website_alert(self, item):
        obj = PreAlertModel.objects.filter(summary=item).first()
        description = obj.description.split()
        url_hash = description[-2]
        result = dict()
        result[self.fingerprint_field] = url_hash
        result['name'] = obj.name
        result['type'] = obj.type
        result['instance'] = obj.instance
        result['port'] = obj.port
        result['cluster'] = AlertModel.AlertType.WEBMONITOR.value
        result['severity'] = obj.severity
        result['summary'] = obj.summary
        result['description'] = " ".join(description[:-2])
        result["start"] = self.timestamp
        result["end"] = self.generate_alert_end_timestamp()
        return result
