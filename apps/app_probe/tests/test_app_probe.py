from django.urls import reverse

from apps.app_global.models import GlobalConfig
from utils.test import get_or_create_user, MyAPITestCase

prometheus_base = """
global:
  scrape_interval: 100s
  evaluation_interval: 100s

scrape_config_files:
  - prometheus_blackbox_http.yml
  - prometheus_blackbox_tcp.yml

remote_write:
  - url: http://mimir/api/v1/push
"""

prometheus_blackbox_http = """
- job_name: '{url_hash}'
    static_configs:
      - targets:
        - '{url}'
    relabel_configs:
        replacement: {local_ip}
"""

prometheus_blackbox_tcp = """
- job_name: '{tcp_hash}'
    static_configs:
      - targets:
        - '{tcp_url}'
        labels:
          url: {tcp_url}
    relabel_configs:
        replacement: {local_ip}
"""

prometheus_exporter_node = """
- job_name: '{url_hash}'l
    params:
      module: [http_2xx]
"""

prometheus_exporter_tidb = """
- job_name: '{url_hash}'
    params:
      module: [http_2xx]
"""

prometheus_exporter_ceph = """
- job_name: '{url_hash}'
    params:
      module: [http_2xx]
"""


class ProbeTestClass(MyAPITestCase):

    def setUp(self):
        self.user1 = get_or_create_user(username='test@123.com')

    def test_app_probe(self):
        base_url = reverse('probe-api:task-version')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['version', 'server'], response.data)

        GlobalConfig.objects.filter(name__startswith='prometheus').delete()

        base_url = reverse('probe-api:task-sbumit_probe')
        data = {
            "operate": "add",
            "version": 0,
            "task": {
                "url": "tcp://ser.cn/",
                "url_hash": "sdfsdfsdfsfsdfsdf",
                "is_tamper_resistant": False
            }
        }
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 500)  # prometheus 配置

        GlobalConfig.objects.create(name='prometheus_service_url', value='http://127.0.0.1:9090')
        GlobalConfig.objects.create(name='prometheus_base', value=prometheus_base)
        GlobalConfig.objects.create(name='prometheus_blackbox_http', value=prometheus_blackbox_http)
        GlobalConfig.objects.create(name='prometheus_blackbox_tcp', value=prometheus_blackbox_tcp)
        GlobalConfig.objects.create(name='prometheus_exporter_ceph', value=prometheus_exporter_ceph)
        GlobalConfig.objects.create(name='prometheus_exporter_node', value=prometheus_exporter_node)
        GlobalConfig.objects.create(name='prometheus_exporter_tidb', value=prometheus_exporter_tidb)

        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 200)

        # 添加 - task 参数为空
        data = {
            "operate": "add",
            "version": 0,
            "task": {
                "url": "",
                "url_hash": "",
                "is_tamper_resistant": ""
            }
        }

        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)
        # 添加 - url 空
        data = {
            "operate": "add",
            "version": 0,
            "task": {
                "url": "",
                "url_hash": "dfjewr980",
                "is_tamper_resistant": False
            }
        }

        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)
        # 添加 - url_hash, is_tamper_resistant 空
        data = {
            "operate": "add",
            "version": 0,
            "task": {
                "url": "http://127.0.0.1:80",
                "url_hash": "",
                "is_tamper_resistant": ""
            }
        }

        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)

        # 添加 - is_tamper_resistant 空
        data = {
            "operate": "add",
            "version": 0,
            "task": {
                "url": "http://127.0.0.1:80",
                "url_hash": "sdjfwiefnwejkr",
                "is_tamper_resistant": ""
            }
        }

        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)

        # 版本 - 无
        data = {
            "operate": "add",
            "version": "",
            "task": {
                "url": "https://baidu.com/",
                "url_hash": "33322222",
                "is_tamper_resistant": False
            }
        }

        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)

        data = {
            "operate": "add",
            "version": 0,
            "task": {
                "url": "https://baidu.com/",
                "url_hash": "33322222",
                "is_tamper_resistant": False
            }
        }

        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 200)

        # 更新
        data = {
            "operate": "update",
            "version": 22,
            "task": {
                "url": "https://baidu.com/",
                "url_hash": "33322222",
                "is_tamper_resistant": False
            },
            "newtask": {
                "url": "http://baidu.com/",
                "url_hash": "weweqwqwewr",
                "is_tamper_resistant": True
            }
        }
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 200)

        # 更新 - newtask 无
        data = {
            "operate": "update",
            "version": 21,
            "task": {
                "url": "http://baidu.com/",
                "url_hash": "weweqwqwewr",
                "is_tamper_resistant": True
            }
        }
        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)

        # 更新 - newtask 空
        data = {
            "operate": "update",
            "version": 21,
            "task": {
                "url": "http://baidu.com/",
                "url_hash": "weweqwqwewr",
                "is_tamper_resistant": True
            },
            "newtask": {}
        }
        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)

        # 更新 - newtask - url
        data = {
            "operate": "update",
            "version": 21,
            "task": {
                "url": "http://baidu.com/",
                "url_hash": "weweqwqwewr",
                "is_tamper_resistant": True
            },
            "newtask": {"url": 'djsdi'}
        }
        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)

        # 更新 - newtask - url - url_hash
        data = {
            "operate": "update",
            "version": 21,
            "task": {
                "url": "http://baidu.com/",
                "url_hash": "weweqwqwewr",
                "is_tamper_resistant": True
            },
            "newtask": {"url": 'djsdi', "url_hash": 'sdnfwefirfr'}
        }
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 200)

        # 删除
        data = {
            "operate": "delete",
            "version": 0,
            "task": {
                "url": "https://baidu.com/",
                "url_hash": "",
                "is_tamper_resistant": ""
            }
        }

        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)

        data = {
            "operate": "delete",
            "version": 0,
            "task": {
                "url": "https://baidu.com/",
                "url_hash": "fsefewrfwe",
                "is_tamper_resistant": ""
            }
        }

        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 400)

        data = {
            "operate": "delete",
            "version": 0,
            "task": {
                "url": "https://baidu.com/",
                "url_hash": "fsefewrfwe",
                "is_tamper_resistant": False
            }
        }

        response = self.client.post(base_url, data=data)
        print(response.data)
        self.assertEqual(response.status_code, 200)

        data = {
            "operate": "delete",
            "version": 0,
            "task": {
                "url": "https://baidu.com/",
                "url_hash": "33322222",
                "is_tamper_resistant": False
            }
        }

        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 200)
