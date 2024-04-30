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
from apps.app_alert.utils.utils import download
from django.utils import timezone as dj_timezone
from datetime import timedelta
from scripts.task_lock import alert_dingtalk_notify_lock

logger = setup_logger(__name__, __file__)


class DingTalk(object):
    webhook = settings.DINGTALKROBOT.get("WEBHOOK")
    AIOPS_BACKEND = settings.AIOPS_BACKEND_CONFIG
    secret = settings.DINGTALKROBOT.get("SECRET")
    robot = DingtalkChatbot(webhook, secret=secret)

    def __init__(self):
        self.end = DateUtils.timestamp_round(DateUtils.timestamp())
        self.start = self.end - 60
        self.clusters = ["mail_metric", "mail_log"]
        logger.info(f"当前时间范围：{DateUtils.ts_to_date(self.start)}, {DateUtils.ts_to_date(self.end)}")
        self.instance_property_mapping = self.get_instance_property_mapping()

    @staticmethod
    def current_datetime():
        now = DateUtils.now()
        week, hour, minute = now.isoweekday(), now.hour, now.minute
        return week, hour, minute

    def run(self):
        """
        首次提醒
        重复提醒
            1.第一次，告警持续20分钟
            2.第二次，告警持续60分钟
            3.每天早上8:00、下午16:00，推送未处理告警信息
        """
        week, hour, minute = self.current_datetime()
        if hour in [8, 16] and minute == 1:
            self.specific_time_run()
        else:
            self.daily_task_run()

    def daily_task_run(self):
        """
        :return:
        """
        self.metric_notification()
        self.log_notification()
        self.work_order_notification()
        self.repeat_notice(minute=20)  # 持续20分钟还没有恢复的，再次通知
        self.repeat_notice(minute=60)  # 持续60分钟还没有恢复的，再次通知

    def specific_time_run(self):
        self.work_order_notification()
        # 指标类自动恢复告警
        metric_resolved_alerts = self.search_resolved_alerts(alert_type="metric")
        title, record = self.metric_alert_format(metric_resolved_alerts, "Resolved")
        if record:
            self.post(title, record)
        # 指标类长时间未解决 重复通知
        metric_firing_alerts = self.search_firing_alerts(alert_type="metric", start=0, end=self.end)
        title, record = self.metric_alert_format(metric_firing_alerts, "Firing", minute=-1)
        if record:
            self.post(title, record)
        # 日志类长时间未解决 重复通知
        log_alerts = self.search_firing_alerts(alert_type="log", start=0, end=self.end)
        title, record = self.log_alert_format(log_alerts, minute=-1)
        if record:
            self.post(title, record)

    def repeat_notice(self, minute):
        # 指标类长时间未解决 重复通知
        metric_alerts = self.search_firing_alerts(
            alert_type="metric",
            start=self.start - minute * 60,
            end=self.end - minute * 60)
        title, record = self.metric_alert_format(metric_alerts, "Firing", minute=minute)
        if record:
            self.post(title, record)

        # 日志类长时间未解决 重复通知
        log_alerts = self.search_firing_alerts(
            alert_type="log",
            start=self.start - minute * 60,
            end=self.end - minute * 60)
        title, record = self.log_alert_format(log_alerts, minute=minute)
        if record:
            self.post(title, record)

    def get_instance_property_mapping(self):
        try:
            url = f'{self.AIOPS_BACKEND.get("API")}/api/v1/mail/ipaddress/property/'
            auth = self.AIOPS_BACKEND.get("AUTH")
            resp = download(method="get", url=url, auth=auth)
            return resp.json()
        except:
            return {}

    def search_firing_alerts(self, alert_type, start, end):
        with MysqlManager() as client:
            sql = f'select * from alert_firing where ' \
                  f'{start} < creation and creation <= {end} and type="{alert_type}";'
            alerts = []
            result = client.search(sql)
            for alert in result:
                if not self.alert_cluster_filter(alert):
                    continue
                if self.has_created_work_order(alert):
                    continue
                alerts.append(alert)
            return alerts

    def search_resolved_alerts(self, alert_type):
        with MysqlManager() as client:
            sql = f'select * from alert_resolved where ' \
                  f'{self.start} < modification and modification <= {self.end} and type="{alert_type}";'
            result = client.search(sql)
            alerts = []
            for alert in result:
                if not self.alert_cluster_filter(alert):
                    continue
                if self.has_created_work_order(alert):
                    logger.info("该自动恢复的指标告警已经创建工单")
                    continue
                alerts.append(alert)
            return alerts

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
            sql = f'select * from alert_work_order where creation>"{self.start}" and creation<="{self.end}";'
            work_orders = client.search(sql)
            for order in work_orders:
                alert_id = order.get("alert_id")
                creator_id = order.get("creator_id")
                alert = client.search(f'select * from alert_firing where id="{alert_id}";') or client.search(
                    f'select * from alert_resolved where id="{alert_id}";')
                alert = alert[0]
                if not self.alert_cluster_filter(alert):
                    continue
                creator = client.search(
                    f'select last_name,first_name,email from users_userprofile where id="{creator_id}";')
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
        """
        指标类告警通知
        :return:
        """
        logger.info("指标告警通知")
        # 新触发告警
        metric_alerts = self.search_firing_alerts(alert_type="metric", start=self.start, end=self.end)
        title, record = self.metric_alert_format(metric_alerts, "Firing")
        if record:
            self.post(title, record)

        # 自动恢复告警
        resolved_alerts = self.search_resolved_alerts(alert_type="metric")
        title, record = self.metric_alert_format(resolved_alerts, "Resolved")
        if record:
            self.post(title, record)

    def log_notification(self):
        """
        日志类告警通知
        :return:
        """
        logger.info("日志类告警通知")
        log_alerts = self.search_firing_alerts(alert_type="log", start=self.start, end=self.end)
        title, record = self.log_alert_format(log_alerts)
        if record:
            self.post(title, record)

    def work_order_notification(self):
        """
        告警工单通知
        :return:
        """
        alerts = self.search_work_order()
        if not alerts:
            return
        collected_alerts = self.group_by_collect(alerts)
        for collect_id, collect_alerts in collected_alerts.items():
            title, record = self.work_order_format(collect_id, collect_alerts)
            self.post(title, record)

    def group_by_collect(self, alerts):
        mapping = dict()
        for alert in alerts:
            collect = alert.get('collect')
            if not mapping.get(collect):
                mapping[collect] = []
            mapping[collect].append(alert)
        return mapping

    def alert_cluster_filter(self, alert):
        if alert.get("cluster") in self.clusters:
            return True

    @staticmethod
    def parse_alert_instance(alert):
        instance = alert.get("instance") or ""
        return instance

    def parser_property_info(self, instance):
        instance_property = self.instance_property_mapping.get(instance) or {}
        property_id = "**设备序号**: {}".format(instance_property.get("id") or "")
        property_name = "**设备名称**: {}".format(instance_property.get("name") or "")
        property_director = "**管理员**: {}".format(instance_property.get("director") or "")
        return property_id, property_name, property_director

    def metric_alert_format(self, alerts, status, minute=0):
        if not alerts:
            return '', ''
        alert_status = f"### **指标告警({status})**"
        start = "**告警时间**: {}".format(DateUtils.ts_to_date(alerts[0].get("start")))
        alert_msg_mapping = dict()
        for alert in alerts:
            instance = self.parse_alert_instance(alert)
            if not alert_msg_mapping.get(instance):
                alert_msg_mapping[instance] = []
            description = alert.get("description")
            alert_msg_mapping[instance].append(f"{description}, {alert.get('id')[:10]}")
        record_msg_list = list()
        if minute:
            if minute == -1:
                record_msg_list.append(f'### *Tip:未处理告警信息推送*')
            else:
                record_msg_list.append(f'### *Tip:告警时长超过{minute}分钟*')
        record_msg_list.extend(["---", alert_status, start, "---"])
        for instance, descriptions in alert_msg_mapping.items():
            property_id, property_name, property_director = self.parser_property_info(instance)
            instance_field = "**设备IP**: {}".format(instance)
            record_msg_list.append(property_id)
            record_msg_list.append(property_name)
            record_msg_list.append(instance_field)
            record_msg_list.append(property_director)
            for description in descriptions:
                description = "**告警信息**: {}".format(description)
                record_msg_list.append(description)
            record_msg_list.append("---\n\n")
        return f"指标告警：{list(alert_msg_mapping.keys())[0]}", "\n\n".join(record_msg_list)

    def log_alert_format(self, alerts, minute=0):
        if not alerts:
            return '', ''
        alert_status = "### **日志告警(Firing)**"
        start = "**告警时间**: {}".format(DateUtils.ts_to_date(alerts[0].get("start")))
        alert_msg_mapping = dict()
        for alert in alerts:
            instance = self.parse_alert_instance(alert)
            if not alert_msg_mapping.get(instance):
                alert_msg_mapping[instance] = []
            description = alert.get("description")
            alert_msg_mapping[instance].append(f"{description}, {alert.get('id')[:10]}")
        record_msg_list = list()
        if minute:
            if minute == -1:
                record_msg_list.append(f'### *Tip:未处理告警信息推送*')
            else:
                record_msg_list.append(f'### *Tip:告警时长超过{minute}分钟*')
        record_msg_list.extend(["---", alert_status, start, "---"])
        for instance, descriptions in alert_msg_mapping.items():
            property_id, property_name, property_director = self.parser_property_info(instance)
            instance_field = "**设备IP**: {}".format(instance)
            record_msg_list.append(property_id)
            record_msg_list.append(property_name)
            record_msg_list.append(instance_field)
            record_msg_list.append(property_director)
            for description in descriptions:
                description = "**告警信息**: {}".format(description)
                record_msg_list.append(description)
            record_msg_list.append("---\n\n")
        return f"日志告警：{list(alert_msg_mapping.keys())[0]}", "\n\n".join(record_msg_list)

    def work_order_format(self, collect_id, alerts):
        alert_status = "### **工单处理**"
        start_timestamp = alerts[0].get("creation")
        start = "**创建时间**: {}".format(DateUtils.ts_to_date(start_timestamp))
        # 按照主机IP进行分类
        alert_msg_mapping = dict()
        for alert in alerts:
            instance = self.parse_alert_instance(alert)
            if not alert_msg_mapping.get(instance):
                alert_msg_mapping[instance] = []
            description = alert.get("description")
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
            property_id, property_name, property_director = self.parser_property_info(instance)
            record_msg_list.append(property_id)
            record_msg_list.append(property_name)
            record_msg_list.append("**设备IP**: {}".format(instance))
            record_msg_list.append(property_director)
            for message in messages:
                record_msg_list.append("**告警信息**: {}".format(message.get("description")))
            record_msg_list.append("---\n\n")
        order_message = list(alert_msg_mapping.values())[0][0]
        record_msg_list.append("**创建者**: {}".format(order_message.get("creator")))
        record_msg_list.append("**处理状态**: {}".format(order_message.get("status")))
        record_msg_list.append("**工单备注**: {}".format(order_message.get("remark")))
        record_msg_list.append("---\n\n")
        return f"工单处理：{list(alert_msg_mapping.keys())[0]}", "\n\n".join(record_msg_list)


def run_task_use_lock():
    nt = dj_timezone.now()
    ok, exc = alert_dingtalk_notify_lock.acquire(expire_time=(nt + timedelta(minutes=1)))  # 先拿锁
    if not ok:  # 未拿到锁退出
        return

    run_desc = 'success'
    try:
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
                not alert_dingtalk_notify_lock.start_time
                or (nt - alert_dingtalk_notify_lock.start_time) >= timedelta(seconds=30)  # 定时周期
        ):
            alert_dingtalk_notify_lock.mark_start_task()  # 更新任务执行信息
            DingTalk().run()
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = alert_dingtalk_notify_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            alert_dingtalk_notify_lock.notify_unrelease()


if __name__ == '__main__':
    # while True:
    #     run_task_use_lock()
    #     time.sleep(1)
    run_task_use_lock()
