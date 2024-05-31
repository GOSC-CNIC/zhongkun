import json
import re
from apps.app_alert.utils.utils import download
from apps.app_alert.utils.utils import DateUtils
from django.conf import settings


class EasyOPSAccount(object):
    DOMAIN = settings.EASY_OPS.get('DOMAIN')

    def __init__(self):
        self.token = ''
        self.expire = 0

    def get_headers(self):
        if self.expire > DateUtils.timestamp():
            return {'Authorization': self.token}

        else:
            self.token = self._get_token()
            self.expire = DateUtils.timestamp() + 600
        return {'Authorization': self.token}

    def _get_token(self):
        """
        获取token
        """
        url = f'{self.DOMAIN}/api/v3/auth/login'
        data = {
            "username": settings.EASY_OPS.get('USERNAME'),
            "password": settings.EASY_OPS.get('PASSWORD')
        }
        resp = download(method='post', url=url, json=data)
        text = resp.text
        text = json.loads(text)
        data = text.get('data')
        return data


easyops_account = EasyOPSAccount()


class EasyOPS(object):
    DOMAIN = settings.EASY_OPS.get('DOMAIN')

    def __init__(self):
        self._chart_id_set = set()
        self._chart_list = list()

    def crawler_easyops_chart_list(self):
        self._get_chart_list()
        return self._chart_list

    def _get_menu_id_list(self):
        url = f'{self.DOMAIN}/api/v3/model-factory/tree/nodes-contain-instance-by-relation-end/uplink/port'
        resp = download(method='get', url=url, headers=easyops_account.get_headers())
        return self._parse_menu(resp)

    @staticmethod
    def _parse_menu(resp):
        text = resp.text
        menu_id_list = re.findall('"id":"(.*?)"', text)
        return menu_id_list

    def _get_chart_list(self):
        menu_list = self._get_menu_id_list()
        for menu_id in menu_list:
            self._get_sub_chart_list(menu_id=menu_id)

    def _get_sub_chart_list(self, menu_id):
        url = f'{self.DOMAIN}/api/v3/mrtg/mrtg/instance-ports-in-tree-node/{menu_id}'
        resp = download(method='get', url=url, headers=easyops_account.get_headers())
        return self._parse_chart_list(resp)

    def _parse_chart_list(self, resp):
        text = resp.text
        text = json.loads(text)
        data = text.get('data')
        for item in data:
            item.pop('if_index', '')
            device_ip = item.get("device_ip")
            port_name = item.get("port_name")
            unique_str = f'{device_ip}_{port_name}'
            if unique_str not in self._chart_id_set:
                self._chart_id_set.add(unique_str)
                self._chart_list.append(item)

    def traffic(self, chart, metrics_ids, start, end):
        """
        获取 流量图表
        """
        url = f'{self.DOMAIN}/api/v3/mrtg/mrtg/device-ports-traffic'
        data = {
            "ports": [
                chart,
            ],
            "show_max": True,
            "program": "SNMP",
            "metrics_ids": metrics_ids,
            "end_time": end,
            "start_time": start
        }
        resp = download(method='post', url=url, json=data, headers=easyops_account.get_headers())
        return self.traffic_parser(resp=resp)

    @staticmethod
    def traffic_parser(resp):
        """
        移除 ifHCInOctets_max ifHCOutOctets_max 字段
        """

        text = resp.text
        text = json.loads(text)
        data = text.get('data')
        legends = data.get('legends')
        if 'ifHCInOctets_max' in legends and 'ifHCOutOctets_max' in legends:
            text['data']["legends"].remove('ifHCInOctets_max')
            text['data']["legends"].remove('ifHCOutOctets_max')
            for item in text['data']["data"]:
                item['values'].pop(-1)
                item['values'].pop(-1)
        return text
