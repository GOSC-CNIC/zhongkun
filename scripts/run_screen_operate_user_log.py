import os
import sys
from pathlib import Path
from datetime import timedelta, datetime, timezone

import pytz
import requests
from django import setup
from requests.auth import HTTPBasicAuth

# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from django.utils import timezone as dj_timezone
from apps.app_screenvis.models import ServerService, ObjectService, ServerServiceLog, ObjectServiceLog

from scripts.task_lock import scree_user_operate_log_lock


class ScreenUserOperateLog:

    def build_url(self, service_type, base_url):
        url = None
        if service_type == 'evcloud':
            if base_url.endswith('/'):
                url = f'{base_url}api/v3/logrecord/'
            else:
                url = f'{base_url}/api/v3/logrecord/'
        else:

            if base_url.endswith('/'):
                url = f'{base_url}api/v1/log/user/'
            else:
                url = f'{base_url}/api/v1/log/user/'
        return url


    def write_data_to_sql(self, data, type, server_unit, log_model, tz):
        """写入数据库"""

        for log_data in data:
            timestamp = datetime.fromtimestamp(log_data['create_time'], tz=tz)
            try:
                log_model.objects.create(
                    username=log_data['username'],
                    content=log_data['operation_content'],
                    creation_time=timestamp,
                    service_cell=server_unit
                )
            except Exception as e:
                print(f'{dj_timezone.now()} -- ERROR -- {type} --服务单元 {server_unit.name} 用户操作日志数据信息 {log_data} 未存入数据库, 错误信息：{str(e)}')
                continue



    def do_task(self, url, type, server_unit, log_model):

        req = requests.get(url, auth=HTTPBasicAuth(server_unit.username, server_unit.raw_password()))
        if req.status_code != 200:
            print(f'{dj_timezone.now()} -- ERROR -- {type} --服务单元 {server_unit.name} -- 本次请求错误，错误信息：{req.text}, url {url}')
            return

        data = req.json()['results']

        if not data:
            return
        tz = pytz.timezone('Asia/Shanghai')
        self.write_data_to_sql(data, type, server_unit, log_model, tz)
        next_url = req.json()['next']
        if next_url is not None:
            self.do_task(next_url, type, server_unit, log_model)

        return



    def task(self, services, type):
        """获取数据
        :param services: 服务单元数据
        :param type: 服务单元类型：iharbor/evcloud
        """

        for server in services:
            url = self.build_url(service_type=type, base_url=server.endpoint_url)
            if type == 'evcloud':
                log_data = ServerServiceLog.objects.order_by('-creation_time').first()
                if log_data:
                    timestamp = log_data.creation_time.timestamp()  # 时间戳
                    url = f'{url}?timestamp={timestamp}'
                self.do_task(url=url, type=type, server_unit=server, log_model=ServerServiceLog)
            else:
                log_data = ObjectServiceLog.objects.order_by('-creation_time').first()
                if log_data:
                    timestamp = log_data.creation_time.timestamp()  # 时间戳
                    url = f'{url}?timestamp={timestamp}'
                self.do_task(url=url, type=type, server_unit=server, log_model=ObjectServiceLog)

    def run(self):
        print(f'{datetime.now()} -- 执行脚本获取服务单元用户操作日志')
        server_service = ServerService.objects.all()  # 云主机
        object_service = ObjectService.objects.all()  # 对象存储

        self.task(services=server_service, type='evcloud')
        self.task(services=object_service, type='iharbor')


def main_use_lock():
    nt = dj_timezone.now()
    ok, exc = scree_user_operate_log_lock.acquire(expire_time=(nt + timedelta(minutes=10)))  # 先拿锁
    if not ok:  # 未拿到锁退出
        return

    run_desc = 'success'
    try:
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not scree_user_operate_log_lock.start_time
            or (nt - scree_user_operate_log_lock.start_time) >= timedelta(minutes=10)    # 定时周期
        ):
            scree_user_operate_log_lock.mark_start_task()  # 更新任务执行信息
            ScreenUserOperateLog().run()
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = scree_user_operate_log_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            scree_user_operate_log_lock.notify_unrelease()


if __name__ == "__main__":
    """
    服务单元用户操作日志获取
    """
    main_use_lock()
