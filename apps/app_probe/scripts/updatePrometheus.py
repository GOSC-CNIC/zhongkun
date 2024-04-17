import sys
import os
import requests
from django import setup
from django.utils import timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# 设置项目的配置文件 不做修改的话就是 settings 文件
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudverse.settings")
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


def write_local_prometheus_config(data):
    """写入本地 promethrus 配置中"""

    configTemp = open("/aiops/updatePrometheus/configTempHTTP.yml", mode='w')
    configTempTCP = open("/aiops/updatePrometheus/configTempTCP.yml", mode='w')
    for i in range(len(data)):
        monitorUrl = data[i]['url']
        monitorUrlHash = data[i]['url_hash']

        if monitorUrl.find("http") > -1:
            template2 = open("/aiops/updatePrometheus/prometheusTemplateHTTP.yml", mode='r')
            configLine = template2.readline()
            while configLine:
                configLine = configLine.replace("greatMonitorURL", monitorUrl)
                configLine = configLine.replace("greatMonitorurl_hash", monitorUrlHash)
                # configLine=configLine.replace("webNumber","web"+str(i))
                configTemp.write(configLine)
                configLine = template2.readline()
            template2.close()
        if monitorUrl.find("tcp") > -1:
            monitorUrl = monitorUrl.replace("tcp://", "").replace("/", "")
            template2 = open("/aiops/updatePrometheus/prometheusTemplateTCP.yml", mode='r')
            configLine = template2.readline()
            while configLine:
                configLine = configLine.replace("greatMonitorURL", monitorUrl)
                configLine = configLine.replace("greatMonitorurl_hash", monitorUrlHash)
                # configLine=configLine.replace("webNumber","web"+str(i))
                configTempTCP.write(configLine)
                configLine = template2.readline()
            template2.close()
    configTemp.close()
    configTempTCP.close()

    promeConfig = open("/etc/prometheus/prometheus.yml", mode='w')
    template = open("/aiops/updatePrometheus/prometheusTemplate1.yml", mode='r')
    configLine = template.readline()
    while configLine:
        promeConfig.write(configLine)
        configLine = template.readline()
    template.close()

    template = open("/aiops/updatePrometheus/configTempHTTP.yml", mode='r')
    configLine = template.readline()
    while configLine:
        promeConfig.write(configLine)
        configLine = template.readline()
    template.close()

    template = open("/aiops/updatePrometheus/configTempTCP.yml", mode='r')
    configLine = template.readline()
    while configLine:
        promeConfig.write(configLine)
        configLine = template.readline()
    template.close()

    template = open("/aiops/updatePrometheus/prometheusTemplate3.yml", mode='r')
    configLine = template.readline()
    while configLine:
        promeConfig.write(configLine)
        configLine = template.readline()
    template.close()
    promeConfig.close()
    os.system("curl -X POST http://localhost:9090/-/reload")


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
                    uri=task['url'],
                )
            except Exception as e:
                print(f'{timezone.now()} -- 添加任务 url 信息有误，路径：{next_task_list_url} =》 {str(e)}')
                pass

        init_data = init_data + data  # 合并数据

        if next_flag:
            next_task_list_url = f'{task_list_url}?marker={next_marker}'
        else:
            return init_data


def main():
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

    init_data = get_task_data(task_list_url=task_list_url, next_task_list_url=next_task_list_url)
    try:
        write_local_prometheus_config(data=init_data)
    except Exception as e:
        print(f'{timezone.now()} -- 写入配置文件有误 =》 {str(e)}')


"""
        http://ip:9090/api/v1/query?query=probe_http_duration_seconds{url=%22http://xxx/%22}  # 查询 时间
        http://ip:9090/api/v1/query?query=probe_http_status_code{url=%22http://www.cemps.cas.cn/%22}  # 查询 状态
"""


def get_url_status():
    """"
    {
    "status": "success",
    "data": {
        "resultType": "vector",
        "result": [
            {
                "metric": {
                    "__name__": "probe_http_status_code",
                    "group": "web",
                    "instance": "127.0.0.1:9115",
                    "job": "027874e4df99b76b14ceff719e72655772d202ed",
                    "url": "http://www.cemps.cas.cn/"
                },
                "value": [
                    1713259560.001,
                    "200"
                ]
            }
        ]
    }
}

    """
    url = 'http://127.0.0.1:9090/api/v1/query?query=probe_http_status_code'   # 多个
    response = requests.get(url)
    if response.status_code != 200:
        return

    data = response.json()['data']['result']
    for task in data:
        try:
            md5_path = task['metric']['job']
            url_status = task['value'][1]
        except Exception as e:
            continue

        web_task = ProbeMonitorWebsite.objects.filter(url_hash=md5_path).first()
        if not web_task:
            continue

        web_task.status = url_status
        web_task.save(update_fields=['status'])


def get_url_time():
    """获取响应时间

    {
    "status": "success",
    "data": {
        "resultType": "vector",
        "result": [
            {
                "metric": {
                    "__name__": "probe_http_duration_seconds",
                    "group": "web",
                    "instance": "127.0.0.1:9115",
                    "job": "014ba7063411595889271baf38fc4f02d1da1855",
                    "phase": "connect",
                    "url": "http://xxx/"
                },
                "value": [
                    1713259419.597,
                    "0.001092659"
                ]
            },
            {
                "metric": {
                    "__name__": "probe_http_duration_seconds",
                    "group": "web",
                    "instance": "127.0.0.1:9115",
                    "job": "014ba7063411595889271baf38fc4f02d1da1855",
                    "phase": "processing",
                    "url": "http://xxx/"
                },
                "value": [
                    1713259419.597,
                    "0.012274074"
                ]
            },
            {
                "metric": {
                    "__name__": "probe_http_duration_seconds",
                    "group": "web",
                    "instance": "127.0.0.1:9115",
                    "job": "014ba7063411595889271baf38fc4f02d1da1855",
                    "phase": "resolve",
                    "url": "http://xxx/"
                },
                "value": [
                    1713259419.597,
                    "0.000913727"
                ]
            },
            {
                "metric": {
                    "__name__": "probe_http_duration_seconds",
                    "group": "web",
                    "instance": "127.0.0.1:9115",
                    "job": "014ba7063411595889271baf38fc4f02d1da1855",
                    "phase": "tls",
                    "url": "http://xxx/"
                },
                "value": [
                    1713259419.597,
                    "0"
                ]
            },
            {
                "metric": {
                    "__name__": "probe_http_duration_seconds",
                    "group": "web",
                    "instance": "127.0.0.1:9115",
                    "job": "014ba7063411595889271baf38fc4f02d1da1855",
                    "phase": "transfer",
                    "url": "http://xxx/"
                },
                "value": [
                    1713259419.597,
                    "0.00130656"
                ]
            }
        ]
    }
}

 http://ip:9090/api/v1/query?query=probe_http_duration_seconds{url=%22http://xxx/%22}  # 查询 时间   一个一个查太慢

 http://xxxx:9090/api/v1/query?query=probe_http_duration_seconds
    """

    url = f'http://127.0.0.1:9090/api/v1/query?query=probe_http_duration_seconds'
    response = requests.get(url)
    if response.status_code != 200:
        return

    data = response.json()
    info = data['data']['result']
    for time_task in info:
        job = time_task['metric']['job']
        web_task = ProbeMonitorWebsite.objects.filter(url_hash=job).first()
        if not web_task:
            continue

        time_type = time_task['metric']['phase']
        if time_type == 'transfer':
            transfer = float(time_task['value'][1])
            transfer = float(f'{transfer * 1000:.2f}')
            web_task.transfer_time = transfer
            web_task.save(update_fields=['transfer_time'])
            continue
        elif time_type == 'connect':
            connect = float(time_task['value'][1])
            connect = float(f'{connect * 1000:.2f}')
            web_task.connect_time = connect
            web_task.save(update_fields=['connect_time'])
            continue
        elif time_type == 'processing':
            processing = float(time_task['value'][1])
            processing = float(f'{processing * 1000:.2f}')
            web_task.processing_time = processing
            web_task.save(update_fields=['processing_time'])
            continue
        elif time_type == 'resolve':
            resolve = float(time_task['value'][1])
            resolve = float(f'{resolve * 1000:.2f}')
            web_task.resolve_time = resolve
            web_task.save(update_fields=['resolve_time'])
            continue
        elif time_type == 'tls':
            tls = float(time_task['value'][1])
            tls = float(f'{tls * 1000:.2f}')
            web_task.tls_time = tls
            web_task.save(update_fields=['tls_time'])
            continue


if __name__ == '__main__':
    main()
    # get_url_status()
    # get_url_time()

