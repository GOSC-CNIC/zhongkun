from urllib.parse import urlencode

import requests
from django.utils import timezone
from django.conf import settings

from monitor.models import TotalReqNum


def get_today_start_time():
    nt = timezone.now()
    return nt.replace(hour=0, minute=0, second=0, microsecond=0)


class ServiceReqCounter:
    PORTAL_REQ_NUM_LOKI_SITES = settings.PORTAL_REQ_NUM_LOKI_SITES

    def __init__(self):
        self.today_start_time = get_today_start_time()

    def run(self):
        print(f'Start，时间{self.today_start_time}向前一天请求数统计')
        req_num_ins = TotalReqNum.get_instance()
        if req_num_ins.until_time == self.today_start_time:
            print(f'END，已统计过 时间{self.today_start_time}向前一天请求数。')
            return

        preday_num = self.get_sites_req_num(sites=self.PORTAL_REQ_NUM_LOKI_SITES)
        req_num_ins.req_num += preday_num
        req_num_ins.until_time = self.today_start_time
        req_num_ins.modification = timezone.now()
        req_num_ins.save(update_fields=['req_num', 'until_time', 'modification'])
        print(f'END，时间{self.today_start_time}向前一天请求数: {preday_num}，总数：{req_num_ins.req_num}。')

    def get_sites_req_num(self, sites: dict):
        """
        sites: [{'api': 'https://x.x.1.x:44135/loki/api/v1/query', 'job': 'servicebackend'}]
        """
        preday_req_num = 0
        until_timestamp = int(self.today_start_time.timestamp())
        for site in sites:
            api = site.get('api', '')
            job = site.get('job', '')
            try:
                r_num = self.get_site_req_num(api=api, job=job, until_timestamp=until_timestamp)
            except Exception:
                r_num = 0

            preday_req_num += r_num

        return preday_req_num

    def get_site_req_num(self, api: str, job: str, until_timestamp: int):
        value = f'count_over_time({{job="{job}"}}[1d])'
        querys_str = urlencode(query={'query': value, 'time': until_timestamp})
        url = f'{api.rstrip("/")}?{querys_str}'

        try:
            req_num = self.do_get_num(url=url)
        except Exception:
            req_num = self.do_get_num(url=url)

        return req_num

    @staticmethod
    def do_get_num(url: str):
        try:
            r = requests.get(url=url)
        except Exception:
            r = requests.get(url=url)

        data = r.json()
        if 300 > r.status_code >= 200:
            s = data.get('status')
            if s == 'success':
                result = data['data']['result']
                value = result[0]['value']
                return int(value[1])

        msg = f"status: {r.status_code}, errorType: {data.get('errorType')}, error: {data.get('error')}"
        return Exception(msg)
