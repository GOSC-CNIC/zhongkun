import sys
import os
import requests
from django.utils import timezone
from apps.app_probe.models import ProbeDetails, ProbeMonitorWebsite
from core import errors


class ProbeHandlers:

    def get_probe_details(self):
        """获取探针信息"""
        return ProbeDetails().get_instance()

    def get_local_probe_version(self):
        """获取本地版本号"""
        probe_obj = self.get_probe_details()

        return probe_obj.version

    def update_version(self, version: int):
        """更新版本信息"""
        local_version = self.get_local_probe_version()

        if local_version != version:
            inst = self.get_probe_details()
            inst.version = version
            inst.save(update_fields=['version'])
            return True

        return False

    @staticmethod
    def get_probe_website(task: dict):

        try:
            obj = ProbeMonitorWebsite.objects.filter(url_hash=task['url_hash'], url=task['url']).first()
        except Exception as e:
            raise errors.Error(message=f'查询探针网站监控任务错误：{str(e)}')

        if not obj:
            return None

        return obj

    def add_probe_website(self, task: dict):
        """添加一条url信息"""

        try:
            obj = self.get_probe_website(task=task)
        except errors.Error as e:
            raise e

        if obj:
            return True

        try:
            ProbeMonitorWebsite.objects.create(
                url_hash=task['url_hash'],
                is_tamper_resistant=task['is_tamper_resistant'],
                url=task['url'],
            )
        except Exception as e:
            raise errors.Error(message=f'创建探针网站监控任务错误：{str(e)}')

        return True

    def delete_probe_website(self, task: dict):
        """删除一条url记录"""

        try:
            obj = self.get_probe_website(task=task)
        except errors.Error as e:
            raise e

        if not obj:
            return True

        try:
            obj.delete()
        except Exception as e:
            raise errors.Error(message=f'删除探针网站监控任务错误：{str(e)}')
        return True

    def update_probe_website(self, task: dict, newtask:dict):
        """更新一条url记录"""

        try:
            obj = self.get_probe_website(task=task)
        except errors.Error as e:
            raise e

        if not obj:
            return self.add_probe_website(task=task)

        update_fields_list = []
        if newtask['url'] and newtask['url'] != obj.url:
            obj.url = newtask['url']
            update_fields_list.append('url')

        if newtask['url_hash'] and newtask['url_hash'] != obj.url_hash:
            obj.url_hash = newtask['url_hash']
            update_fields_list.append('url_hash')

        if newtask['is_tamper_resistant'] and newtask['is_tamper_resistant'] != obj.is_tamper_resistant:

            obj.is_tamper_resistant = newtask['is_tamper_resistant']
            update_fields_list.append('is_tamper_resistant')

        if update_fields_list:
            obj.save(update_fields=update_fields_list)

            return True

        return None

    # def get_website_version(self):
    #     """远程获取监控版本号"""
    #
    #     respond = requests.get(self.website_version_url)
    #     if respond.status_code != 200:
    #         print(f'{timezone.now()} -- 查询版本信息有误 =》 {respond.text}')
    #         return None
    #
    #     respond = respond.json()
    #     return respond['version']
    #
    # def get_website_task(self, task_list_url):
    #     respond = requests.get(task_list_url)
    #     if respond.status_code != 200:
    #         print(f'{timezone.now()} -- 查询任务信息有误 =》 {respond.text}')
    #         return None, None, None
    #     respond = respond.json()
    #     return respond['results'], respond['has_next'], respond['next_marker']
    #
    # def write_prometheus_http_tcp_template(self, template2, monitor_url, monitor_url_hash, config_temp_tcp_or_http):
    #     config_line = template2.readline()
    #     while config_line:
    #         config_line = config_line.replace("greatMonitorURL", monitor_url)
    #         config_line = config_line.replace("greatMonitorurl_hash", monitor_url_hash)
    #         # configLine=configLine.replace("webNumber","web"+str(i))
    #         config_temp_tcp_or_http.write(config_line)
    #         config_line = template2.readline()
    #     template2.close()
    #
    # def update_prometheus_config_yml(self, data):
    #     """更新 prometheus http tcp 配置文件"""
    #
    #     config_temp = open("/aiops/updatePrometheus/configTempHTTP.yml", mode='w')
    #     config_temp_tcp = open("/aiops/updatePrometheus/configTempTCP.yml", mode='w')
    #
    #     for i in range(len(data)):
    #
    #         monitor_url = data[i]['url']
    #         monitor_url_hash = data[i]['url_hash']
    #
    #         if monitor_url.find("http") > -1:
    #             template2 = open("/aiops/updatePrometheus/prometheusTemplateHTTP.yml", mode='r')
    #             self.write_prometheus_http_tcp_template(template2=template2, monitor_url=monitor_url,
    #                                                     monitor_url_hash=monitor_url_hash,
    #                                                     config_temp_tcp_or_http=config_temp)
    #         if monitor_url.find("tcp") > -1:
    #             monitor_url = monitor_url.replace("tcp://", "").replace("/", "")
    #             template2 = open("/aiops/updatePrometheus/prometheusTemplateTCP.yml", mode='r')
    #             self.write_prometheus_http_tcp_template(template2=template2, monitor_url=monitor_url,
    #                                                     monitor_url_hash=monitor_url_hash,
    #                                                     config_temp_tcp_or_http=config_temp_tcp)
    #
    #     config_temp.close()
    #     config_temp_tcp.close()
    #
    # def write_config_yal_template(self, template, prome_config):
    #     """写入配置文件模板"""
    #     config_line = template.readline()
    #     while config_line:
    #         prome_config.write(config_line)
    #         config_line = template.readline()
    #     template.close()
    #
    # def write_local_prometheus_config(self, data):
    #     """写入本地 promethrus 配置中"""
    #
    #     self.update_prometheus_config_yml(data=data)
    #
    #     prome_config = open("/etc/prometheus/prometheus.yml", mode='w')
    #     template = open("/aiops/updatePrometheus/prometheusTemplate1.yml", mode='r')
    #     self.write_config_yal_template(template=template, prome_config=prome_config)
    #
    #     template = open("/aiops/updatePrometheus/configTempHTTP.yml", mode='r')
    #     self.write_config_yal_template(template=template, prome_config=prome_config)
    #
    #     template = open("/aiops/updatePrometheus/configTempTCP.yml", mode='r')
    #     self.write_config_yal_template(template=template, prome_config=prome_config)
    #
    #     template = open("/aiops/updatePrometheus/prometheusTemplate3.yml", mode='r')
    #     self.write_config_yal_template(template=template, prome_config=prome_config)
    #
    #     prome_config.close()
    #     os.system("curl -X POST http://localhost:9090/-/reload")
    #
    # def get_task_data(self, task_list_url, next_task_list_url):
    #     """获取任务数据"""
    #     init_data = []
    #     ProbeMonitorWebsite.objects.all().delete()  # 清空数据表
    #
    #     while True:
    #
    #         data, next_flag, next_marker = self.get_website_task(task_list_url=next_task_list_url)
    #
    #         for task in data:
    #             try:
    #                 ProbeMonitorWebsite.objects.create(
    #                     url_hash=task['url_hash'],
    #                     is_tamper_resistant=task['is_tamper_resistant'],
    #                     url=task['url'],
    #                 )
    #             except Exception as e:
    #                 print(f'{timezone.now()} -- 添加任务 url 信息有误，路径：{next_task_list_url} =》 {str(e)}')
    #                 pass
    #
    #         init_data = init_data + data  # 合并数据
    #
    #         if next_flag:
    #             next_task_list_url = f'{task_list_url}?marker={next_marker}'
    #         else:
    #             return init_data
    #
    # def main(self, version):
    #     """"""
    #     next_task_list_url = task_list_url = self.website_task_url
    #
    #     obj = self.get_probe_details()
    #     if not obj:
    #         try:
    #             obj = ProbeDetails.objects.create(version=version, probe_type=1)
    #         except Exception as e:
    #             print(f'{timezone.now()} -- 创建默认探针信息有误 =》 {str(e)}')
    #             return
    #
    #     if obj.version == version:
    #         return
    #
    #     obj.version = version
    #     obj.save(update_fields=['version'])
    #
    #     init_data = self.get_task_data(task_list_url=task_list_url, next_task_list_url=next_task_list_url)
    #     try:
    #         self.write_local_prometheus_config(data=init_data)
    #     except Exception as e:
    #         print(f'{timezone.now()} -- 写入配置文件有误 =》 {str(e)}')
