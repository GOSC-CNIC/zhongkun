import os

from apps.app_probe.models import ProbeDetails, ProbeMonitorWebsite
from core import errors
from core.loggers import config_script_logger

probe_logger = config_script_logger(name='app-probe-handler', filename='app_probe.log')


class ProbeHandlers:

    def get_probe_details(self):
        """获取探针信息"""
        return ProbeDetails().get_instance()

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
        local_version = self.get_local_probe_version()

        if local_version != version:
            inst = self.get_probe_details()
            inst.version = version
            inst.save(update_fields=['version'])
            return True

        return False

    @staticmethod
    def get_probe_website(task: dict):
        """获取监控任务的一条数据"""

        try:
            obj = ProbeMonitorWebsite.objects.filter(url_hash=task['url_hash'], url=task['url'],
                                                     is_tamper_resistant=task['is_tamper_resistant']).first()
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

        try:
            self.handler_prometheus_config()
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

        try:
            self.handler_prometheus_config()
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

            try:
                self.handler_prometheus_config()
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

    def handler_prometheus_config(self):
        from apps.app_global.models import GlobalConfig

        base_path = '/etc/prometheus/prometheus.yml'
        path_http = '/etc/prometheus/prometheus_blackbox_http.yml'
        path_tcp = '/etc/prometheus/prometheus_blackbox_tcp.yml'
        path_exporter_node = '/etc/prometheus/prometheus_exporter_node.yml'
        path_exporter_tidb = '/etc/prometheus/prometheus_exporter_tidb.yml'
        path_exporter_ceph = '/etc/prometheus/prometheus_exporter_ceph.yml'

        prometheus_query_name_list = [
            GlobalConfig.ConfigName.PROMETHEUS_BASE.value,
            GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_TIDB.value,
            GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_CEPH.value,
            GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_NODE.value,
            GlobalConfig.ConfigName.PROMETHEUS_BLACKBOX_HTTP.value,
            GlobalConfig.ConfigName.PROMETHEUS_BLACKBOX_TCP.value,
            GlobalConfig.ConfigName.PROMETHEUS_SERVICE_URL.value,

        ]

        prometheus_configs = GlobalConfig.objects.filter(
            name__in=prometheus_query_name_list).all()

        if not prometheus_configs:
            raise Exception('请到全局配置表中添加 prometheus 相关配置')

        prometheus_config = prometheus_configs.filter(name=prometheus_query_name_list[0]).first()

        if not prometheus_config:
            raise Exception('请到全局配置表中添加 prometheus 基础配置文件')

        prometheus_url = prometheus_configs.filter(name=prometheus_query_name_list[6]).first()
        if not prometheus_url:
            raise Exception('未找到prometheus_url 信息，请到全局配置表中配置')

        if prometheus_config.name == prometheus_query_name_list[0]:
            self.write_prometheus_config(path=base_path, prometheus_base_yml=prometheus_config.value)

        website = self.get_probe_monitor_website()

        for prometheus in prometheus_configs:

            if prometheus.name == prometheus_query_name_list[1] and prometheus.value:
                self.write_prometheus_config_tidb(path=path_exporter_tidb, prometheus_base_tidb_yml=prometheus.value)

            if prometheus.name == prometheus_query_name_list[2] and prometheus.value:
                self.write_prometheus_config_ceph(path=path_exporter_ceph, prometheus_base_ceph_yml=prometheus.value)

            if prometheus.name == prometheus_query_name_list[3] and prometheus.value:
                self.write_prometheus_config_node(path=path_exporter_node, prometheus_base_node_yml=prometheus.value)

            if prometheus.name == prometheus_query_name_list[4] and prometheus.value:
                try:
                    self.write_probe_http_config(website=website, prometheus_blackbox_http_yml=prometheus.value,
                                                 path_http=path_http)
                except Exception as e:
                    raise Exception(f'写入prometheus_blackbox_http.yml文件时错误:{str(e)}')

            if prometheus.name == prometheus_query_name_list[5] and prometheus.value:
                try:
                    self.write_probe_tcp_config(website=website, prometheus_blackbox_tcp_yml=prometheus.value,
                                                path_tcp=path_tcp)
                except Exception as e:
                    raise Exception(f'写入prometheus_blackbox_tcp.yml文件时错误:{str(e)}')

        if not prometheus_url.value.endswith('/'):
            prometheus_url.value += '/'

        os.system(f"curl -X POST {prometheus_url.value}-/reload")
