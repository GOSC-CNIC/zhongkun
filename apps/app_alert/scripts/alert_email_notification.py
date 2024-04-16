"""
告警邮件通知定时任务
"""

import os
import sys
import re
import traceback
from django import setup
from pathlib import Path

# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()
from apps.app_alert.models import AlertModel
from apps.app_alert.models import EmailNotification
from apps.app_alert.models import ScriptFlagModel
from apps.app_alert.utils.logger import setup_logger
from apps.app_alert.utils.utils import custom_model_to_dict
from apps.app_alert.utils.utils import DateUtils
from django.contrib.contenttypes.models import ContentType
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db.utils import IntegrityError

try:  # TODO
    from apps.app_monitor.managers import MonitorWebsiteManager
except:
    from apps.monitor.managers import MonitorWebsiteManager

try:
    from apps.app_monitor.apiviews.monitor_views import UnitAdminEmailViewSet
except:
    from apps.monitor.apiviews.monitor_views import UnitAdminEmailViewSet

logger = setup_logger(__name__, __file__)


class EmailThresholdStrict(object):
    """
    邮件发送阈值
    每天从早7点开始计算：
        1，一天内给每个邮箱发邮件不超过4封
        2，一小时内每个邮箱发邮件不超过1封
        3，四小时内每个邮箱发邮件不超过2封
    """

    def __init__(self, timestamp, email_list):
        self.timestamp = timestamp
        self.timetuple = DateUtils.beijing_timetuple()
        self.email_list = email_list
        self.day_start, self.day_end = self.get_day_interval()
        self.one_hour_list = [(_, _ + 3600) for _ in range(self.day_start, self.day_end, 3600)]
        self.four_hour_list = [(_, _ + 3600 * 4) for _ in range(self.day_start, self.day_end, 3600 * 4)]
        # 当前处于的时间区间
        self.one_range = self.pick_hour_range(self.one_hour_list)
        self.two_range = self.pick_hour_range(self.four_hour_list)
        self.mapping = dict()

    def get_day_interval(self):
        today_seven_timestamp = DateUtils.date_to_ts(
            dt=f"{self.timetuple.tm_year}-{self.timetuple.tm_mon}-{self.timetuple.tm_mday} 07:00:00",
            fmt="%Y-%m-%d %H:%M:%S")

        start = today_seven_timestamp if self.timetuple.tm_hour >= 7 else today_seven_timestamp - 86400
        return start, start + 86400

    def pick_hour_range(self, rang_list):
        for _ in rang_list:
            if _[0] <= self.timestamp <= _[-1]:
                return _

    def start(self):
        for email in self.email_list:
            if not self.mapping.get(email):
                self.mapping[email] = dict()
            self.mapping[email][(self.day_start, self.day_end)] = \
                self.search_sent_counts(email, (self.day_start, self.day_end))
            self.mapping[email][self.one_range] = self.search_sent_counts(email, self.one_range)
            self.mapping[email][self.two_range] = self.search_sent_counts(email, self.two_range)
        return self.mapping

    @staticmethod
    def search_sent_counts(email, _range):
        count = EmailNotification.objects.filter(
            email=email,
            timestamp__gte=_range[0],
            timestamp__lte=_range[1]).values("timestamp").distinct().count()
        return count


class NotificationSender(object):
    feint = False  # 测试

    def __init__(self, timestamp, monitor_alerts_mapping, filter_mapping):
        self.timestamp = timestamp
        self.monitor_alerts_mapping = monitor_alerts_mapping
        self.filter_mapping = filter_mapping

    def start(self):
        for email, alerts in self.monitor_alerts_mapping.items():
            user_sent_mapping = self.filter_mapping.get(email)
            if not self.should_to_send(user_sent_mapping):
                logger.info(f"{user_sent_mapping} , {email}账号已经达到发送的上限，本次不发送邮件通知.")
                continue
            subject, message = self.html_content(email, alerts, user_sent_mapping)
            if self.feint is True:
                continue

            # 记录到邮件发送记录表
            self.record_notification(alerts)
            # 更新告警的发送时间
            self.update_notification_timestamp(alerts)
            # # 发送通知
            pool = ThreadPoolExecutor(max_workers=1)
            pool.submit(self.send_to_monitor, receiver=email, subject=subject, message=message)
            pool.shutdown(wait=False)

    def record_notification(self, alerts):
        """
        记录邮件通知发送
        """
        logger.info("写入邮件通知记录表")
        for alert in alerts:
            obj = {
                "alert": alert.get("id"),
                "email": alert.get("email"),
                "timestamp": DateUtils.timestamp_round(self.timestamp),
            }
            logger.info(str(obj))
            EmailNotification.objects.create(**obj)

    def send_to_monitor(self, receiver, subject, message):
        logger.info(message)
        email_model = ContentType.objects.get(app_label="users", model="email").model_class()
        email = email_model.send_email(
            subject=subject, receivers=[receiver],
            message='', html_message=message,
            tag=email_model.Tag.API.value, fail_silently=False,
            save_db=True, remote_ip='127.0.0.1', is_feint=self.feint
        )
        logger.info("邮件发送状态：{}".format(email))

    @staticmethod
    def should_to_send(user_sent_mapping):
        values = list(user_sent_mapping.values())
        if values[0] < 4 and values[1] < 1 and values[2] < 2:
            return True
        else:
            return False

    @staticmethod
    def upper_limit_text(user_sent_mapping):
        index = 0
        for _range, count in user_sent_mapping.items():
            index += 1
            if index == 1 and count == 3:
                ts = _range[-1]
                break
            if index == 3 and count == 1:
                ts = _range[-1]
                break
            if index == 2 and count == 0:
                ts = _range[-1]
                break
        else:
            return ''
        if ts:
            date = DateUtils.ts_to_date(ts)
            return f'邮件通知已达到上限，{date}前将不再发送通知。'

    def update_notification_timestamp(self, alerts):
        logger.info("更新首次发送时间戳、上次发送时间戳")
        send_timestamp = DateUtils.timestamp_round(self.timestamp)
        last_id_list = []
        first_id_list = []
        for alert in alerts:
            last_id_list.append(alert.get("id"))
            first_notification = alert.get("first_notification")
            if not first_notification:
                first_id_list.append(alert.get("id"))
        for alert in alerts:
            obj = AlertModel.objects.filter(id=alert.get("id")).first()
            obj.last_notification = send_timestamp
            if not obj.first_notification:
                obj.first_notification = send_timestamp
            obj.save()
            logger.info(f"{obj.id, obj.first_notification, obj.last_notification}")

    @staticmethod
    def update_sql_format(table, field, value, id_list):
        return "update {} set {}={} where id in ({});".format(table, field, value, ",".join(
            ["'{}'".format(_) for _ in id_list]))

    def generate_email_subject(self, unit_mapping):
        """
        生成邮件标题
        """
        subject = ""
        alert_count = 0
        for unit, alerts in unit_mapping.items():
            instance = self.parse_instance(alerts[0])
            if not subject:
                if unit == "网站异常监控":
                    subject = f"网站告警({instance})"
                else:
                    subject = f"主机告警({instance})"
            alert_count += len(alerts)
        if alert_count > 1:
            subject = f"{subject}等"
        return subject

    def html_content(self, email, alerts, sent_mapping):
        """
        重写
        """
        unit_mapping = dict()
        for _ in alerts:
            unit = _.get("unit_name")
            if not unit_mapping.get(unit):
                unit_mapping[unit] = []
            unit_mapping[unit].append(_)
        sub_tables = []
        for unit, unit_alerts in unit_mapping.items():
            sub_table = self.generate_sub_table(unit, unit_alerts)
            sub_tables.append(sub_table)
        sub_tables = "\n".join(sub_tables)
        subject = self.generate_email_subject(unit_mapping)
        limit_message = self.upper_limit_text(sent_mapping)
        content = f"""
            <!DOCTYPE html>
                <html>
                <head>
                <meta charset="UTF-8">
                <style>
                .wrapper{{align-content: center; width: 1400px; height: 100%; margin: 40px auto;
                font-size: 20px; color: black; background-color:rgba(0,0,0,0.01);}}
                a:hover{{color: rebeccapurple;}}
                a{{color: rgb(46,117,181);}}
                table{{width: 100%; text-align: center; margin-top: 20px; font-size: 15px; word-break : break-all;
                border: 1px solid gray; border-spacing: 0; border-collapse: collapse;}}
                tr,td{{border: 1px solid gray; padding: 6px;}}
                .description{{text-align: left;}}
                .title1 {{background-color: rgb(46,117,181); color: white; font-size: 18px;}}
                .title2{{background-color: rgb(222,234,246);}}
                caption{{text-align: left; padding-left: 40px; font-size: 20px;}}
                .nav{{vertical-align: middle; height: 60px; border-top: 100px; background-color: #f5f5f5;
                content: ""; display: block; clear: both;}}
                .nav .logo{{line-height: 50px; float: left;}}
                .nav .main{{line-height: 60px;float: left;padding-left: 2px;}}
                .section{{margin-top: 20px;}}
                .text-indent{{padding-left: 40px;}}
                .t-sec{{font-size: 10px;color: rgba(108, 108, 96, 0.78);}}
                </style>
                </head>
                <body style="width: 100%;" >
                <div class="wrapper">
                <div class="nav">
                <div class="logo">
                <a href="https://service.cstcloud.cn/"><img style="vertical-align: middle; height: 40px" src="https://service.cstcloud.cn/app/main/img/cstcloud_logo.22d98e7b.png"/></a>
                </div>
                <!--<div class="main"><span style="font-size: 21px;">一体化云服务与智能运管平台</span></div>-->
                </div>
                <div>
                <p>尊敬的管理员 {email}，您好！<br/>
                <!--<span class="text-indent">感谢您使用中国科技云一体化云服务与智能运管平台，您的监控集群中有以下异常告警，请及时进行检查。-->
                <span class="text-indent">您的监控集群中有以下异常告警，建议您及时对告警信息进行检查。
                </span>
                </p>
                </div>
                <div>
                <table>
                {sub_tables}
                </table>
                </div>
                <div class="text-indent"><p>{limit_message}</p>
                <p>欢迎登录中国科技云一体化智能运维系统（<a target="view_window" href="https://aiops.cstcloud.cn/my/alert/">https://aiops.cstcloud.cn/my/alert/</a>）查询更多信息。</p></div>
                </div>
                </body>
                </html>
        """
        return subject, content

    def generate_sub_table(self, unit, unit_alerts):
        sub_title = f'<tr><td colspan="9" class="title1">{unit}</td></tr>'
        columns = '<tr class="title2"><td style="width: 1%;">序号</td><td style="width: 5%;">告警实例</td>' \
                  '<td style="width: 4%;">触发时间</td><td style="width: 2%;">告警ID</td><td style="width: 10%;">告警摘要</td>'
        sub_table = [sub_title, columns]
        collect_alerts = dict()
        for alert in unit_alerts:
            instance = self.parse_instance(alert)
            if not collect_alerts.get(instance):
                collect_alerts[instance] = dict()
            _id = alert.get("id")[:8]
            name = alert.get("name")
            start = alert.get("start")
            summary = alert.get("summary")
            severity = alert.get("severity")
            if not collect_alerts[instance].get(summary):
                collect_alerts[instance][summary] = {"_id": _id, "start": start, "name": name, "severity": severity,
                                                     "summary": summary, "description": []}
            description = alert.get("description")
            sub_description = [f"ID: &nbsp;{_id}", f"详情:&nbsp;{description}",
                               f"触发时间: &nbsp;{DateUtils.ts_to_date(start)}"]
            collect_alerts[instance][summary]["description"].append("<br/><br/>".join(sub_description))
        index = 0
        for instance, instance_alert in collect_alerts.items():
            flag = 0
            index += 1
            summary_list = list(instance_alert.values())
            index_len = sum([len(_.get("description")) for _ in summary_list])
            for alert in summary_list:
                _id = alert.get("_id")
                name = alert.get("name")
                severity = alert.get("severity")
                summary = alert.get("summary")
                start = alert.get("start")
                start = DateUtils.ts_to_date(start)
                description = alert.get("description")
                desc_len = len(description)
                for sub_index, desc in enumerate(description):
                    flag += 1
                    sub_index += 1
                    if flag == 1 and sub_index == 1:
                        # tr = f'<tr class="content">' \
                        #      f'<td rowspan="{index_len}">{index}</td><td rowspan="{index_len}">{instance}</td>' \
                        #      f'<td rowspan="{desc_len}">{name}</td><td rowspan="{desc_len}">{severity}</td>' \
                        #      f'<td rowspan="{desc_len}">{summary}</td></tr>'
                        tr = f'<tr class="content">' \
                             f'<td rowspan="{index_len}">{index}</td><td rowspan="{index_len}">{instance}</td>' \
                             f'<td rowspan="{desc_len}">{start}</td><td rowspan="{desc_len}">{_id}</td><td rowspan="{desc_len}">{summary}</td></tr>'
                    elif sub_index == 1:
                        tr = f'<tr class="content">' \
                             f'<td rowspan="{desc_len}">{start}</td><td rowspan="{desc_len}">{_id}</td><td rowspan="{desc_len}">{summary}</td></tr>'
                    else:
                        tr = f'<tr class="content"></tr>'
                    sub_table.append(tr)
        return "\n".join(sub_table)

    @staticmethod
    def parse_instance(alert):
        if alert.get("type") == "webmonitor":
            return re.findall(r'\(instance(.*)\)', alert.get("summary"))[0].strip()
        elif alert.get("instance"):
            return alert.get("instance")
        else:
            return ""


class AlertMonitor(object):
    """
    1.根据当前时间和告警类型，挑选出将要发送的异常任务

    2.判断每个异常任务要通知到的监控者列表

    3.根据监控着邮箱进行汇总

    4.邮件格式封装

    5.发送邮件

    6.更新发送时间

    """

    def __init__(self):
        self.one_hour = 3600
        self.timestamp = DateUtils.timestamp()  # 当前时间戳
        self.run_time = DateUtils.timestamp_round(self.timestamp)

        self.monitor_mapping = dict()

    @staticmethod
    def current_datetime():
        now = DateUtils.now()
        week, hour, minute = now.isoweekday(), now.hour, now.minute
        return week, hour, minute

    @staticmethod
    def first_alerts(active_alerts):
        # first_timestamp为空
        return [_ for _ in active_alerts if _.get("first_notification") is None]

    def daily_alerts(self, active_alerts):
        # first_timestamp不为空，且 异常时间 大于等于24小时，小于等于72小时
        return [_ for _ in active_alerts if _.get("first_notification") and
                24 * self.one_hour <= self.timestamp - _.get("start") <= 72 * self.one_hour]

    def weekly_alerts(self, active_alerts):
        # first_timestamp不为空,且异常时间大于72小时
        return [_ for _ in active_alerts if
                _.get("first_notification") and self.timestamp - _.get("start") > 72 * self.one_hour]

    def frequency_filter(self, alerts):
        """
        如果当前网站异常最近通知过，过滤掉
        """
        return alerts

    def pick_alerts_by_datetime(self):
        """
        根据当前时间和告警类型，挑选出将要发送的异常任务
        """
        # 挑选出 firing alerts
        firing_alerts = self.get_firing_alerts()
        # 根据当前是周几、几点、几分钟 过滤异常
        week, hour, minute = self.current_datetime()
        if week == 1 and hour == 8 and minute == 0:
            logger.info("周八点：选出首次任务、每日任务、每周任务")
            first = self.first_alerts(firing_alerts)
            daily = self.daily_alerts(firing_alerts)
            weekly = self.weekly_alerts(firing_alerts)
            return first + daily + weekly
        elif hour == 8 and minute == 0:
            logger.info("每日八点：选出首次任务、每日任务")
            first = self.first_alerts(firing_alerts)
            daily = self.daily_alerts(firing_alerts)
            return first + daily
        else:
            logger.info("选出首次任务")
            first = self.first_alerts(firing_alerts)
            return self.frequency_filter(first)  # 最近通知过，进行过滤

    def generate_alert_email_list(self, alerts):
        """
        {
            "monitor1":[],
            "monitor2":[],
            "monitor3":[],
            ...
        }
        """
        items = []
        for alert in alerts:
            monitor = self.get_email_list(alert)
            if not monitor:
                continue
            unit_name = monitor.get("unit").get("name")
            monitor_emails = monitor.get("emails")
            for email in monitor_emails:
                item = {"email": email, "unit_name": unit_name}
                item.update(alert)
                items.append(item)
        return items

    @staticmethod
    def group_alert_by_monitor(items):
        mapping = dict()
        for item in items:
            email = item.get("email")
            if not mapping.get(email):
                mapping[email] = list()
            mapping[email].append(item)
        return mapping

    @staticmethod
    def get_firing_alerts():
        """
        可重写
        查询当前 正在进行中的告警
        """
        queryset = AlertModel.objects.all().order_by("instance", "start")
        return [custom_model_to_dict(_) for _ in queryset]

    def get_email_list(self, alert):
        alert_type = alert.get("type")
        if alert_type == "webmonitor":
            return self.get_website_monitor_list(alert)
        elif alert_type in ["metric", "log"]:
            return self.get_cluster_monitor_list(alert)

    @staticmethod
    def _yunkun_cluster_monitor_list(tag):
        unit = UnitAdminEmailViewSet().try_get_unit(tag=tag)
        odc_id = unit.org_data_center_id
        unit_admin_emails = set(unit.users.values_list('username', flat=True))
        org_data_center_model = ContentType.objects.get(app_label="service", model="orgdatacenter").model_class()
        if odc_id:
            odc_admin_emails = set(
                org_data_center_model.objects.get(id=odc_id).users.values_list('username', flat=True))
            unit_admin_emails.update(odc_admin_emails)
        emails = list(set(unit_admin_emails))
        result = {
            'tag': tag,
            'unit': {
                'name': unit.name, 'name_en': unit.name_en
            },
            'emails': emails
        }
        return result

    def get_cluster_monitor_list(self, alert):
        """
        获取 非网站类告警 监控者邮箱列表
        """
        cluster = alert.get("cluster")
        if cluster in ["mail_metric", "mail_log"]:  # TODO
            return None
        if self.monitor_mapping.get(cluster):
            return self.monitor_mapping.get(cluster)
        text = self._yunkun_cluster_monitor_list(cluster)
        self.monitor_mapping[cluster] = text
        return text

    @staticmethod
    def get_website_monitor_list(alert):
        """
        获取网站类告警的监控者列表
        """
        url_hash = alert.get("fingerprint")
        emails = MonitorWebsiteManager.get_site_user_emails(url_hash=url_hash)
        result = {
            "tag": "webmonitor",
            "unit": {"name": "网站异常监控"},
            "emails": [_.get("email") for _ in emails]
        }
        return result

    def check_flag(self, script_name):
        try:
            flag = ScriptFlagModel.objects.create(**{
                'name': script_name,
                'start': self.run_time,
            })
            return flag
        except IntegrityError as e:
            return

    def run(self):
        flag = self.check_flag('email_notification')
        if flag is None:
            logger.info('flag is null.')
            return
        try:
            self._run()
            flag.status = ScriptFlagModel.Status.FINISH.value
            flag.end = DateUtils.timestamp()
            flag.save()
        except Exception as e:
            exc = str(traceback.format_exc())
            logger.info(exc)
            flag.status = ScriptFlagModel.Status.ABORT.value
            flag.end = DateUtils.timestamp()
            flag.save()

    def _run(self):
        logger.info(f"\n\n\n\n开始...{DateUtils.now()}", )
        logger.info("挑选异常告警")
        alerts = self.pick_alerts_by_datetime()
        logger.info("查询每个异常告警的监控者列表")
        alerts = self.generate_alert_email_list(alerts)
        logger.info("根据监控邮箱号进行分组")
        monitor_alerts_mapping = self.group_alert_by_monitor(alerts)
        filter_mapping = EmailThresholdStrict(
            timestamp=self.timestamp,
            email_list=monitor_alerts_mapping.keys()
        ).start()
        logger.info("发送邮件通知并记录通知")
        NotificationSender(
            timestamp=self.timestamp,
            monitor_alerts_mapping=monitor_alerts_mapping,
            filter_mapping=filter_mapping
        ).start()
        logger.info(f"结束...{DateUtils.now()}", )


if __name__ == '__main__':
    AlertMonitor().run()
