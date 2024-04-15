"""
告警钉钉通知定时任务
"""
import re
import os
import sys
import time
from django import setup
from pathlib import Path

# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()
from dingtalkchatbot.chatbot import DingtalkChatbot
from apps.app_alert.utils.utils import DateUtils
from apps.app_alert.utils.logger import setup_logger
from django.conf import settings
from apps.app_alert.utils.db_manager import MysqlManager
from apps.app_alert.models import ScriptFlagModel
from django.db.utils import IntegrityError
import traceback

logger = setup_logger(__name__, __file__)


class DingTalk(object):
    webhook = settings.DINGTALKROBOT.get("WEBHOOK")
    secret = settings.DINGTALKROBOT.get("SECRET")
    robot = DingtalkChatbot(webhook, secret=secret)

    def __init__(self):
        self.end = int(int(time.time() / 60) * 60)
        self.start = self.end - 60
        self.start_date = DateUtils.ts_to_date(self.start)
        self.end_date = DateUtils.ts_to_date(self.end)
        self.clusters = ["mail_metric", "mail_log"]
        logger.info(f"当前时间范围：{self.start_date}, {self.end_date}")

    def check_flag(self, script_name):
        try:
            flag = ScriptFlagModel.objects.create(**{
                'name': script_name,
                'start': self.end,
            })
            return flag
        except IntegrityError as e:
            return

    def run(self):
        flag = self.check_flag('dingtalk_notification')
        if flag is None:
            logger.info('flag is null.')
            return
        try:
            self._run()
            flag.status = ScriptFlagModel.Status.FINISH.value
            flag.end = int(time.time())
            flag.save()
        except Exception as e:
            exc = str(traceback.format_exc())
            logger.info(exc)
            flag.status = ScriptFlagModel.Status.ABORT.value
            flag.end = int(time.time())
            flag.save()

    def _run(self):
        self.metric_notification()
        self.log_notification()
        self.work_order_notification()

    def search_firing_alerts(self, alert_type):
        with MysqlManager() as client:
            sql = f'select * from alert_firing where ' \
                  f'{self.start} < creation and creation <= {self.end} and type="{alert_type}";'
            return client.search(sql)

    def search_resolved_alerts(self, alert_type):
        with MysqlManager() as client:
            sql = f'select * from alert_resolved where ' \
                  f'{self.start} < modification and modification <= {self.end} and type="{alert_type}";'
            return client.search(sql)

    @staticmethod
    def has_created_work_order(alert):
        """
        判断该告警是否已经创建工单
        """
        with MysqlManager() as client:
            sql = f'select * from alert_work_order where alert_id="{alert.get("id")}";'
            return client.search(sql)

    def search_work_order(self):
        """
        挑选出上一分钟创建的工单，进行通知
        """
        alerts = []
        with MysqlManager() as client:
            sql = f'select * from alert_work_order where creation>"{self.start_date}" and creation<="{self.end_date}";'
            work_orders = client.search(sql)
            for order in work_orders:
                alert_id = order.get("alert_id")
                creator_id = order.get("creator_id")
                alert = client.search(f'select * from alert_firing where id="{alert_id}";') or client.search(
                    f'select * from alert_resolved where id="{alert_id}";')
                alert = alert[0]
                if not self.alert_cluster_filter(alert):
                    continue
                creator = client.search(f'select last_name,first_name,email from user where id="{creator_id}";')
                creator = creator[0] if creator else {}
                order.pop("id")
                order.pop("alert_id")
                alert.update(order)
                alert.update(creator)
                alerts.append(alert)
        return alerts

    def post(self, title, text):
        if not title or not text:
            return
        ret = self.robot.send_markdown(title=title, text=text)
        logger.info(str(ret))

    def metric_notification(self):
        logger.info("指标类通知")
        # 新的告警
        for alert in self.search_firing_alerts(alert_type="metric"):
            if not self.alert_cluster_filter(alert):
                continue
            title, record = self.metric_alert_format(alert, "Firing")
            self.post(title, record)

        # 自动恢复告警
        for alert in self.search_resolved_alerts(alert_type="metric"):
            if not self.alert_cluster_filter(alert):
                continue
            if self.has_created_work_order(alert):
                logger.info("该自动恢复的指标告警已经创建工单")
                continue
            title, record = self.metric_alert_format(alert, "Resolved")
            self.post(title, record)

    def log_notification(self):
        logger.info("日志类通知")
        firing_log_alerts = []
        for alert in self.search_firing_alerts(alert_type="log"):
            if not self.alert_cluster_filter(alert):
                continue
            firing_log_alerts.append(alert)
        if not firing_log_alerts:
            return
        title, record = self.log_alert_format(firing_log_alerts)
        self.post(title, record)

    def work_order_notification(self):
        alerts = self.search_work_order()
        if not alerts:
            return
        title, record = self.work_order_format(alerts)
        self.post(title, record)

    def alert_cluster_filter(self, alert):
        if alert.get("cluster") in self.clusters:
            return True

    @staticmethod
    def parse_alert_instance(alert):
        instance = alert.get("instance") or ""
        if alert.get("type") == "metric":
            return instance
        description = alert.get("description")
        alias = re.findall('{"name":"(.*?)"},{"log_source"', description)
        alias = alias[0] if alias else ""
        if alias == "NET-MON":
            alias = ""
        if instance and alias:
            return f"{alias}({instance})"
        elif instance:
            return instance
        else:
            return alias

    def parse_log_description(self, alert):
        description = alert.get("description")
        keywords = ["source: .*? ", "level: .*? ", "content: ", ',{"name":".*?"},{"log_source":".*?"}']
        for keyword in keywords:
            description = re.sub(keyword, "", description)
        return description

    def metric_alert_format(self, alert, status):
        alert_status = "**状态**: {}".format(status)
        start = "**时间**: {}".format(DateUtils.ts_to_date(alert.get("start"), "%Y-%m-%d %H:%M:%S"))
        alert_type = "**类别**: {}".format(alert.get("type"))
        alert_name = "**名称**: {}".format(alert.get("name"))
        severity = "**级别**: {}".format(alert.get("severity"))
        instance = "**主机**: {}".format(self.parse_alert_instance(alert))
        _id = f"**ID**: {alert.get('id')[:10]}"
        summary = "**摘要**: {}".format(alert.get("summary"))
        description = "**详情**: {}".format(alert.get("description"))
        record = ["---", "**指标告警**", alert_status, start, alert_type, alert_name, severity, instance, _id, summary,
                  description, "---"]
        record = "\n\n".join(record)
        return alert.get("name"), record

    def log_alert_format(self, alerts):
        alert_status = "**日志告警**"
        start = "**时间**: {}".format(DateUtils.ts_to_date(alerts[0].get("start"), "%Y-%m-%d %H:%M:%S"))
        alert_msg_mapping = dict()
        for alert in alerts:
            instance = self.parse_alert_instance(alert)
            if not alert_msg_mapping.get(instance):
                alert_msg_mapping[instance] = []
            description = self.parse_log_description(alert)
            alert_msg_mapping[instance].append(f"{description}, {alert.get('id')[:10]}")
        record_msg_list = ["---", alert_status, start, "---"]
        for instance, descriptions in alert_msg_mapping.items():
            instance = "**设备名称**: {}".format(instance)
            record_msg_list.append(instance)
            for description in descriptions:
                description = "**告警信息**: {}".format(description)
                record_msg_list.append(description)
            record_msg_list.append("---\n\n")
        return f"日志告警：{list(alert_msg_mapping.keys())[0]}", "\n\n".join(record_msg_list)

    def work_order_format(self, alerts):
        alert_status = "**工单处理**"
        start = "**时间**: {}".format(str(alerts[0].get("creation")).split(".")[0])
        alert_msg_mapping = dict()
        for alert in alerts:
            instance = self.parse_alert_instance(alert)
            if not alert_msg_mapping.get(instance):
                alert_msg_mapping[instance] = []
            description = self.parse_log_description(alert)
            description = f"{description}, {alert.get('id')[:10]}"
            creator = f"{alert.get('last_name')}{alert.get('first_name')}({alert.get('email')})"
            status = alert.get("status")
            remark = alert.get("remark")
            alert_msg_mapping[instance].append({
                "description": description,
                "creator": creator,
                "status": status,
                "remark": remark,
            })
        record_msg_list = ["---", alert_status, start, "---"]
        for instance, messages in alert_msg_mapping.items():
            for message in messages:
                record_msg_list.append("**设备名称**: {}".format(instance))
                record_msg_list.append("**告警信息**: {}".format(message.get("description")))
                record_msg_list.append("**状态**: {}".format(message.get("status")))
                record_msg_list.append("**备注**: {}".format(message.get("remark")))
                record_msg_list.append("**创建者**: {}".format(message.get("creator")))
                record_msg_list.append("---\n\n")
        return f"工单处理：{list(alert_msg_mapping.keys())[0]}", "\n\n".join(record_msg_list)


if __name__ == '__main__':
    DingTalk().run()
