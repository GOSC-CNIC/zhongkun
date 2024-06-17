import sys
import os
import requests
from django import setup
from django.utils import timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# 设置项目的配置文件 不做修改的话就是 settings 文件
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_site.settings")
setup()

from apps.app_probe.models import ProbeDetails, ProbeMonitorWebsite


def get_website_version(version_url):
    """获取监控版本号"""

    respond = requests.get(version_url)
    if respond.status_code != 200:
        print(f'{timezone.now()} -- 查询版本信息有误 =》 {respond.text}')
        return None

    respond = respond.json()
    return respond['version']


def get_website_task(task_list_url):
    respond = requests.get(task_list_url)
    if respond.status_code != 200:
        print(f'{timezone.now()} -- 查询任务信息有误 =》 {respond.text}')
        return None, None, None
    respond = respond.json()
    return respond['results'], respond['has_next'], respond['next_marker']


def get_task_data(task_list_url, next_task_list_url):
    """获取任务数据"""
    init_data = []
    ProbeMonitorWebsite.objects.all().delete()  # 清空数据表

    while True:

        data, next_flag, next_marker = get_website_task(task_list_url=next_task_list_url)

        for task in data:
            try:
                ProbeMonitorWebsite.objects.create(
                    url_hash=task['url_hash'],
                    is_tamper_resistant=task['is_tamper_resistant'],
                    url=task['url'],
                )
            except Exception as e:
                print(f'{timezone.now()} -- 添加任务 url 信息有误，路径：{next_task_list_url} =》 {str(e)}')
                pass

        init_data = init_data + data  # 合并数据

        if next_flag:
            next_task_list_url = f'{task_list_url}?marker={next_marker}'
        else:
            return init_data


def get_zk_website_task():
    """
    一次性将站点信息写到数据库中
    """
    version_url = "http://servicebackend.cstcloud.cn/api/monitor/website-task/version"
    next_task_list_url = task_list_url = "http://servicebackend.cstcloud.cn/api/monitor/website-task"
    try:
        version = get_website_version(version_url=version_url)
    except Exception as e:
        print(f'{timezone.now()} -- 查询版本号出现错误 =》 {str(e)}')
        return

    if not version:
        print(f'{timezone.now()} -- 未找到版本号信息')
        return

    try:
        obj = ProbeDetails().get_instance()
    except Exception as e:
        print(f'{timezone.now()} -- 查询探针信息有误， 检查是否将探针信息填写完整 =》 {str(e)}')
        return

    if not obj:
        try:
            obj = ProbeDetails.objects.create(version=version, probe_type=1)
        except Exception as e:
            print(f'{timezone.now()} -- 创建默认探针信息有误 =》 {str(e)}')
            return

    if obj.version != version:
        obj.version = version
        obj.save(update_fields=['version'])

    get_task_data(task_list_url=task_list_url, next_task_list_url=next_task_list_url)

    return


if __name__ == '__main__':
    get_zk_website_task()
