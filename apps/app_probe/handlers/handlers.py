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
            need_update_blackbox_type = 'http'
        else:
            need_update_blackbox_type = 'tcp'

        try:
            self.update_prometheus_blackbox_http_tcp(blackbox_type=need_update_blackbox_type)
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
            need_update_blackbox_type = 'http'
        else:
            need_update_blackbox_type = 'tcp'

        try:
            self.update_prometheus_blackbox_http_tcp(blackbox_type=need_update_blackbox_type)
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
                need_update_blackbox_type = 'http'
            else:
                need_update_blackbox_type = 'tcp'

            try:
                self.update_prometheus_blackbox_http_tcp(blackbox_type=need_update_blackbox_type)
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
        :param prometheus_base_yml: promtheus基础配置文件内容
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
        :param prometheus_base_ceph_yml: promtheus exporter ceph 配置文件
        """

        try:
            self.write_yml(path, prometheus_base_ceph_yml)
        except Exception as e:
            raise Exception(f'写入prometheus_exporter_ceph.yml文件时错误：{str(e)}')

    def write_prometheus_config_node(self, path, prometheus_base_node_yml):
        """写入 prometheus 配置文件
        :param path:  # path = '/etc/prometheus/prometheus.yml'
        :param prometheus_base_node_yml:
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

    def update_prometheus_exporter_node_yml(self, obj: GlobalConfig = None):
        """更新 prometheus exorpter node """

        if obj and obj.value:
            try:
                self.write_prometheus_config_node(
                    path=self.path_exporter_node, prometheus_base_node_yml=obj.value)
            except Exception as e:
                raise Exception(f'写入prometheus_exporter_node.yml文件时错误:{str(e)}')

            self.reload_prometheus_config()
            return

        yml_template = GlobalConfig.objects.filter(name=GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_NODE.value).first()
        if not yml_template or not yml_template.value:
            raise Exception(f'未找到 “promtheus exporter node 配置文件” 内容')

        try:
            self.write_prometheus_config_node(
                path=self.path_exporter_node, prometheus_base_node_yml=yml_template.value)
        except Exception as e:
            raise Exception(f'写入prometheus_exporter_node.yml文件时错误:{str(e)}')

        self.reload_prometheus_config()

    def update_prometheus_exporter_tidb_yml(self, obj: GlobalConfig = None):
        """更新 prometheus exorpter tidb """

        if obj and obj.value:
            try:
                self.write_prometheus_config_tidb(
                    path=self.path_exporter_tidb, prometheus_base_tidb_yml=obj.value)
            except Exception as e:
                raise Exception(f'写入prometheus_exporter_tidb.yml文件时错误:{str(e)}')

            self.reload_prometheus_config()
            return

        yml_template = GlobalConfig.objects.filter(name=GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_TIDB.value).first()
        if not yml_template or not yml_template.value:
            raise Exception(
                f'未找到 prometheus_exporter_tidb配置内容，请到 站点参数中配置"promtheus exporter tidb 配置文件"')

        try:
            self.write_prometheus_config_tidb(
                path=self.path_exporter_tidb, prometheus_base_tidb_yml=yml_template.value)
        except Exception as e:
            raise Exception(f'写入prometheus_exporter_tidb.yml文件时错误:{str(e)}')

        self.reload_prometheus_config()

    def update_prometheus_exporter_ceph_yml(self, obj: GlobalConfig = None):
        """更新 prometheus exorpter ceph """

        if obj and obj.value:
            try:
                self.write_prometheus_config_ceph(
                    path=self.path_exporter_ceph, prometheus_base_ceph_yml=obj.value)
            except Exception as e:
                raise Exception(f'写入prometheus_exporter_ceph.yml文件时错误:{str(e)}')

            self.reload_prometheus_config()
            return

        yml_template = GlobalConfig.objects.filter(name=GlobalConfig.ConfigName.PROMETHEUS_EXPORTER_CEPH.value).first()
        if not yml_template or not yml_template.value:
            raise Exception(f'未找到 "promtheus exporter ceph 配置文件"内容, 请到站点参数中配置')

        try:
            self.write_prometheus_config_ceph(
                path=self.path_exporter_ceph, prometheus_base_ceph_yml=yml_template.value)
        except Exception as e:
            raise Exception(f'写入prometheus_exporter_ceph.yml文件时错误:{str(e)}')

        self.reload_prometheus_config()

    def update_prometheus_yml(self, obj: GlobalConfig = None):
        """更新 prometheus yml """

        if obj and obj.value:
            try:
                self.write_prometheus_config(path=self.base_path, prometheus_base_yml=obj.value)
            except Exception as e:
                raise Exception(f'写入prometheus.yml文件时错误:{str(e)}')

            self.reload_prometheus_config()
            return

        yml_template = GlobalConfig.objects.filter(name=GlobalConfig.ConfigName.PROMETHEUS_BASE.value).first()
        if not yml_template or not yml_template.value:
            raise Exception(f'未找到 "promtheus基础配置文件"内容, 请到站点参数里设置')

        try:
            self.write_prometheus_config(path=self.base_path, prometheus_base_yml=yml_template.value)
        except Exception as e:
            raise Exception(f'写入prometheus.yml文件时错误:{str(e)}')

        self.reload_prometheus_config()

    def update_prometheus_blackbox_http_yml(self):
        """更新 prometheus http """
        website_qs = self.get_probe_monitor_website()  # 数据集

        if not website_qs:
            return

        yml_template = GlobalConfig.objects.filter(name=GlobalConfig.ConfigName.PROMETHEUS_BLACKBOX_HTTP.value).first()
        if not yml_template or not yml_template.value:
            raise Exception(f'未找到 "promtheus blackbox http 配置文件模板"内容')

        try:
            self.write_probe_http_config(website=website_qs, prometheus_blackbox_http_yml=yml_template.value,
                                         path_http=self.path_http)
        except Exception as e:
            raise Exception(f'写入prometheus_blackbox_http.yml文件时错误:{str(e)}')

        self.reload_prometheus_config()

    def update_prometheus_blackbox_tcp_yml(self):
        """更新 prometheus tcp """
        website_qs = self.get_probe_monitor_website()  # 数据集

        if not website_qs:
            return

        yml_template = GlobalConfig.objects.filter(name=GlobalConfig.ConfigName.PROMETHEUS_BLACKBOX_TCP.value).first()
        if not yml_template or not yml_template.value:
            raise Exception(f'未找到 "promtheus blackbox tcp 配置文件模板"内容')

        try:
            self.write_probe_tcp_config(website=website_qs, prometheus_blackbox_tcp_yml=yml_template.value,
                                        path_tcp=self.path_tcp)
        except Exception as e:
            raise Exception(f'写入prometheus_blackbox_http.yml文件时错误:{str(e)}')

        self.reload_prometheus_config()

    def update_prometheus_blackbox_http_tcp(self, blackbox_type):
        """"""

        if blackbox_type == "http":
            return self.update_prometheus_blackbox_http_yml()
        else:
            return self.update_prometheus_blackbox_tcp_yml()

    def update_prometheus_service_url(self):
        """prometheus 服务地址更新 """
        prom_service_url = GlobalConfig.objects.filter(
            name=GlobalConfig.ConfigName.PROMETHEUS_SERVICE_URL.value).first()

        if prom_service_url and prom_service_url.value:
            return self.reload_prometheus_config()

    @staticmethod
    def reload_prometheus_config():
        """重新加载 prometheus 服务配置文件 """
        prom_base_url = GlobalConfig.objects.filter(name=GlobalConfig.ConfigName.PROMETHEUS_SERVICE_URL.value).first()
        if not prom_base_url:
            probe_logger.error(f'未找到prometheus服务地址信息内容，请检查站点信息中是否配置')
            return

        if not prom_base_url.value.endswith('/'):
            prom_base_url.value += '/'

        try:
            os.system(f"curl -X POST {prom_base_url.value}-/reload")
        except Exception as e:
            probe_logger.error(f'重新加载prometheus服务失败，请检查服务及端口配置是否正确：{str(e)}')

    def handler_prometheus_config(self, obj: GlobalConfig):
        """"""

        global_config_name = GlobalConfig.ConfigName

        prometheus_globalconfig_list = [
            global_config_name.PROMETHEUS_BASE.value,
            global_config_name.PROMETHEUS_EXPORTER_TIDB.value,
            global_config_name.PROMETHEUS_EXPORTER_CEPH.value,
            global_config_name.PROMETHEUS_EXPORTER_NODE.value,
            global_config_name.PROMETHEUS_BLACKBOX_HTTP.value,
            global_config_name.PROMETHEUS_BLACKBOX_TCP.value,
            global_config_name.PROMETHEUS_SERVICE_URL.value
        ]

        prometheus_globalconfig_name = obj.name

        if prometheus_globalconfig_name not in prometheus_globalconfig_list:
            return

        if prometheus_globalconfig_name == global_config_name.PROMETHEUS_BASE.value:
            try:
                self.update_prometheus_yml(obj=obj)
            except Exception as e:
                raise e

        if prometheus_globalconfig_name == global_config_name.PROMETHEUS_EXPORTER_TIDB.value:
            try:
                self.update_prometheus_exporter_tidb_yml(obj=obj)
            except Exception as e:
                raise e

        if prometheus_globalconfig_name == global_config_name.PROMETHEUS_EXPORTER_CEPH.value:
            try:
                self.update_prometheus_exporter_ceph_yml(obj=obj)
            except Exception as e:
                raise e

        if prometheus_globalconfig_name == global_config_name.PROMETHEUS_EXPORTER_NODE.value:
            try:
                self.update_prometheus_exporter_node_yml(obj=obj)
            except Exception as e:
                raise e

        if prometheus_globalconfig_name == global_config_name.PROMETHEUS_BLACKBOX_HTTP.value:
            try:
                self.update_prometheus_blackbox_http_tcp(blackbox_type='http')
            except Exception as e:
                raise e

        if prometheus_globalconfig_name == global_config_name.PROMETHEUS_BLACKBOX_TCP.value:
            try:
                self.update_prometheus_blackbox_http_tcp(blackbox_type='tcp')
            except Exception as e:
                raise e

        if prometheus_globalconfig_name == global_config_name.PROMETHEUS_SERVICE_URL.value:
            try:
                self.update_prometheus_service_url()
            except Exception as e:
                raise e
