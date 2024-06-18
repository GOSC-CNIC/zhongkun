import os

from apps.app_probe.models import ProbeDetails, ProbeMonitorWebsite
from core import errors
from core.loggers import config_script_logger
from apps.app_global.models import GlobalConfig


probe_logger = config_script_logger(name='app-probe-handler', filename='app_probe.log')


class ProbeHandlers:

    def __init__(self):

        self.base_path = '/etc/prometheus/prometheus.yml'
        self.path_http = '/etc/prometheus/prometheus_blackbox_http.yml'
        self.path_tcp = '/etc/prometheus/prometheus_blackbox_tcp.yml'
        self.path_exporter_node = '/etc/prometheus/prometheus_exporter_node.yml'
        self.path_exporter_tidb = '/etc/prometheus/prometheus_exporter_tidb.yml'
        self.path_exporter_ceph = '/etc/prometheus/prometheus_exporter_ceph.yml'

    def get_probe_details(self):
        """获取探针信息"""

        inst = ProbeDetails().get_instance()
        if inst is None:
            inst = ProbeDetails.objects.create(version=0, probe_name='探针服务')

        return inst

    def get_local_probe_version(self):
        """获取本地版本号"""
        probe_obj = self.get_probe_details()

        return probe_obj.version

    @staticmethod
    def get_probe_monitor_website():
        """获取监控任务的全部数据"""
        return ProbeMonitorWebsite.objects.all()

    def update_version(self, version: int):
        """更新版本信息"""

        if not version or version <= 0:
            return False

        inst = self.get_probe_details()

        if inst.version != version:
            inst.version = version
            inst.save(update_fields=['version'])
            return True

        return False

    @staticmethod
    def get_probe_website(task: dict):
        """获取监控任务的一条数据"""

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

        if task['url'].startswith('http'):
            need_update_prometheus_config_list = ['prometheus_blackbox_http']
        else:
            need_update_prometheus_config_list = ['prometheus_blackbox_tcp']

        if need_update_prometheus_config_list:

            try:
                self.handler_prometheus_config(need_update_prometheus_config_list=need_update_prometheus_config_list)
            except errors.Error as e:
                probe_logger.error(msg=f'添加探针信息后重新加载prometheus配置文件时错误：{str(e)}')
                raise e

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

        if task['url'].startswith('http'):
            need_update_prometheus_config_list = ['prometheus_blackbox_http']
        else:
            need_update_prometheus_config_list = ['prometheus_blackbox_tcp']

        if need_update_prometheus_config_list:
            try:
                self.handler_prometheus_config(need_update_prometheus_config_list=need_update_prometheus_config_list)
            except errors.Error as e:
                probe_logger.error(msg=f'删除探针信息后重新加载prometheus配置文件时错误：{str(e)}')
                raise e

        return True

    def update_probe_website(self, task: dict, newtask: dict):
        """更新一条url记录"""

        try:
            obj = self.get_probe_website(task=task)
        except errors.Error as e:
            raise e

        if not obj:
            return self.add_probe_website(task=task)

        if not newtask:
            raise errors.Error('请添加 newtask 参数')

        try:
            new_task_key_list = list(newtask.keys())
            for key in ['url', 'url_hash', 'is_tamper_resistant']:
                if key not in new_task_key_list:
                    raise Exception(f'请添加 newtask {key} 参数')
        except Exception as e:
            raise errors.BadRequest(message=str(e))

        update_fields_list = []
        if newtask['url'] and newtask['url'] != obj.url:
            obj.url = newtask['url']
            update_fields_list.append('url')

        if newtask['url_hash'] and newtask['url_hash'] != obj.url_hash:
            obj.url_hash = newtask['url_hash']
            update_fields_list.append('url_hash')

        if newtask['is_tamper_resistant']:
            if newtask['is_tamper_resistant'] != obj.is_tamper_resistant:
                obj.is_tamper_resistant = newtask['is_tamper_resistant']
                update_fields_list.append('is_tamper_resistant')
        else:
            if newtask['is_tamper_resistant'] != obj.is_tamper_resistant:
                obj.is_tamper_resistant = newtask['is_tamper_resistant']
                update_fields_list.append('is_tamper_resistant')

        if update_fields_list:
            obj.save(update_fields=update_fields_list)

            if newtask['url'].startswith('http'):
                need_update_prometheus_config_list = ['prometheus_blackbox_http']
            else:
                need_update_prometheus_config_list = ['prometheus_blackbox_tcp']

            if not need_update_prometheus_config_list:
                return True

            try:
                self.handler_prometheus_config(need_update_prometheus_config_list=need_update_prometheus_config_list)
            except errors.Error as e:
                probe_logger.error(msg=f'更新探针信息后重新加载prometheus配置文件时错误：{str(e)}')
                raise e

            return True

        return None

    @staticmethod
    def write_yml(path, yml, flag=False):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            if flag:
                f.write(yml + '\n')
            else:
                # f.write('scrape_configs:' + '\n')
                f.write('  ' + yml + '\n')

    def write_prometheus_config(self, path, prometheus_base_yml):
        """写入 prometheus 配置文件
        :param path:  '/etc/prometheus/prometheus.yml'
        """
        try:
            self.write_yml(path, prometheus_base_yml, flag=True)
        except Exception as e:
            raise Exception(f'写入prometheus.yml文件时错误：{str(e)}')

    def write_prometheus_config_tidb(self, path, prometheus_base_tidb_yml):
        """写入 prometheus 配置文件
        :param path:  # path = '/etc/prometheus/xx_tidb.yml'
        :param prometheus_base_tidb_yml: yml 内容
        """

        try:
            self.write_yml(path, prometheus_base_tidb_yml)
        except Exception as e:
            raise Exception(f'写入prometheus_exporter_tibd.yml文件时错误：{str(e)}')

    def write_prometheus_config_ceph(self, path, prometheus_base_ceph_yml):
        """写入 prometheus 配置文件
        :param path:  # path = '/etc/prometheus/prometheus.yml'
        """

        try:
            self.write_yml(path, prometheus_base_ceph_yml)
        except Exception as e:
            raise Exception(f'写入prometheus_exporter_ceph.yml文件时错误：{str(e)}')

    def write_prometheus_config_node(self, path, prometheus_base_node_yml):
        """写入 prometheus 配置文件
        :param path:  # path = '/etc/prometheus/prometheus.yml'
        """

        try:
            self.write_yml(path, prometheus_base_node_yml)
        except Exception as e:
            raise Exception(f'写入prometheus_exporter_node.yml文件时错误：{str(e)}')

    @staticmethod
    def write_probe_http_config(website, prometheus_blackbox_http_yml, path_http):
        """
        :param website: url 数据
        :param prometheus_blackbox_http_yml:  http 模板
        :param path_http: prometheus http 配置文件路径
        """

        os.makedirs(os.path.dirname(path_http), exist_ok=True)

        with open(path_http, mode='w') as f:
            f.write('scrape_configs:' + '\n')
            for line in website:

                if not line.url.endswith('/'):
                    line.url = line.url + '/'

                if line.url.startswith('http'):
                    yml_http = prometheus_blackbox_http_yml.format(url_hash=line.url_hash, url=line.url,
                                                                   local_ip='127.0.0.1:9115')

                    config = yml_http.replace('\r\n', '\n')  # Windows
                    yml_http = config.replace('\r', '\n')  # MacOS
                    f.write('  ' + yml_http + '\n\n')  # 最后留空行

        return

    @staticmethod
    def write_probe_tcp_config(website, prometheus_blackbox_tcp_yml, path_tcp):
        """
        :param website: url 数据
        :param prometheus_blackbox_tcp_yml:  http 模板
        :param path_tcp: prometheus tcp 配置文件路径
        """

        os.makedirs(os.path.dirname(path_tcp), exist_ok=True)

        with open(path_tcp, mode='w') as f:
            f.write('scrape_configs:' + '\n')

            for line in website:
                if not line.url.endswith('/'):
                    line.url = line.url + '/'

                if line.url.startswith('tcp'):
                    yml_tcp = prometheus_blackbox_tcp_yml.format(tcp_hash=line.url_hash, tcp_url=line.url,
                                                                 local_ip='127.0.0.1:9115')

                    config = yml_tcp.replace('\r\n', '\n')  # Windows
                    yml_tcp = config.replace('\r', '\n')  # MacOS
                    f.write('  ' + yml_tcp + '\n\n')

        return

    def update_prometheus_part_config(self, prometheus_configs):
        """更新部分文件 prometheus"""

        for prometheus in prometheus_configs:
            if prometheus.name == GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_TIDB.value:
                if prometheus.value:
                    self.write_prometheus_config_tidb(
                        path=self.path_exporter_tidb, prometheus_base_tidb_yml=prometheus.value)
            elif prometheus.name == GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_CEPH.value:
                if prometheus.value:
                    self.write_prometheus_config_ceph(
                        path=self.path_exporter_ceph, prometheus_base_ceph_yml=prometheus.value)
            elif prometheus.name == GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_NODE.value:
                if prometheus.value:
                    self.write_prometheus_config_node(
                        path=self.path_exporter_node, prometheus_base_node_yml=prometheus.value)
            elif prometheus.name == GlobalConfig.ConfigName.PROMETHEUS_BLACKBOX_HTTP.value:
                if prometheus.value:
                    website_qs = self.get_probe_monitor_website()

                    try:
                        self.write_probe_http_config(website=website_qs, prometheus_blackbox_http_yml=prometheus.value,
                                                     path_http=self.path_http)
                    except Exception as e:
                        raise Exception(f'写入prometheus_blackbox_http.yml文件时错误:{str(e)}')
            elif prometheus.name == GlobalConfig.ConfigName.PROMETHEUS_BLACKBOX_TCP.value:
                if prometheus.value:
                    website = self.get_probe_monitor_website()

                    try:
                        self.write_probe_tcp_config(website=website, prometheus_blackbox_tcp_yml=prometheus.value,
                                                    path_tcp=self.path_tcp)
                    except Exception as e:
                        raise Exception(f'写入prometheus_blackbox_tcp.yml文件时错误:{str(e)}')
            elif prometheus.name == GlobalConfig.ConfigName.PROMETHEUS_BASE.value:
                self.write_prometheus_config(path=self.base_path, prometheus_base_yml=prometheus.value)

    def handler_prometheus_config(self, need_update_prometheus_config_list: list = None):
        prometheus_query_name_list = [
            GlobalConfig.ConfigName.PROMETHEUS_BASE.value,
            GlobalConfig.ConfigName.PROMETHEUS_SERVICE_URL.value,
        ]

        prometheus_config_list = [
            GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_TIDB.value,
            GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_CEPH.value,
            GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_NODE.value,
            GlobalConfig.ConfigName.PROMETHEUS_BLACKBOX_HTTP.value,
            GlobalConfig.ConfigName.PROMETHEUS_BLACKBOX_TCP.value,
        ]

        if need_update_prometheus_config_list:
            prometheus_query_name_list += need_update_prometheus_config_list
        else:
            prometheus_query_name_list += prometheus_config_list

        prom_config_qs = GlobalConfig.objects.filter(name__in=prometheus_query_name_list).all()
        prom_cfg_objs_dict = {o.name: o for o in prom_config_qs}
        prom_cfg_obj = prom_cfg_objs_dict.get(GlobalConfig.ConfigName.PROMETHEUS_BASE.value, None)
        if not prom_cfg_obj:
            raise Exception('请到全局配置表中添加 prometheus 基础配置文件')

        prom_url_obj = prom_cfg_objs_dict.pop(GlobalConfig.ConfigName.PROMETHEUS_SERVICE_URL.value, None)
        if not prom_url_obj or not prom_cfg_obj.url:
            raise Exception('未找到prometheus_url 信息，请到全局配置表中配置')

        self.update_prometheus_part_config(prometheus_configs=prom_cfg_objs_dict.values())

        if not prom_url_obj.value.endswith('/'):
            prom_url_obj.value += '/'

        os.system(f"curl -X POST {prom_url_obj.value}-/reload")
