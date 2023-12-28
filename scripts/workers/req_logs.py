import asyncio
from urllib.parse import urlencode
from datetime import datetime
from typing import List

import requests
from django.utils import timezone
from django.conf import settings

from monitor.models import TotalReqNum, LogSite, LogSiteTimeReqNum
from monitor.backends.log import LogLokiAPI
from monitor.utils import build_loki_provider


def get_today_start_time():
    nt = timezone.now()
    return nt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_now_hour_start_time():
    nt = timezone.now()
    return nt.replace(minute=0, second=0, microsecond=0)


class ServiceReqCounter:
    PORTAL_REQ_NUM_LOKI_SITES = settings.PORTAL_REQ_NUM_LOKI_SITES

    def __init__(self):
        self.new_until_time = get_now_hour_start_time()

    def run(self) -> int:
        """
        每次最少统计1h、最多统计24h内的请求数，定时执行周期可选1-24小时
        :return: 本次统计的前多少个小时内的请求数
        """
        new_until_time = self.new_until_time
        req_num_ins = TotalReqNum.get_instance()
        # 最大统计24h内的
        hours = self.range_hours(until_time=new_until_time, ins=req_num_ins)
        delta_str = f'时间{new_until_time}向前{hours}小时内请求数'
        if hours == 0:
            print(f'END，已统计过 {delta_str}。')
            return hours

        print(f'Start，{delta_str}统计')
        hours_req_num = self.get_sites_req_num(
            sites=self.PORTAL_REQ_NUM_LOKI_SITES, new_until_time=new_until_time, hours=hours)
        req_num_ins.req_num += hours_req_num
        req_num_ins.until_time = new_until_time
        req_num_ins.modification = timezone.now()
        req_num_ins.save(update_fields=['req_num', 'until_time', 'modification'])
        print(f'END，{delta_str}: {hours_req_num}，总数：{req_num_ins.req_num}。')
        return hours

    @staticmethod
    def range_hours(until_time: datetime, ins: TotalReqNum) -> int:
        if ins.until_time is None:
            return 24

        t_rang = until_time - ins.until_time
        hours = int(t_rang.total_seconds() / 3600)
        # 最大统计24h内的
        hours = min(hours, 24)
        hours = max(hours, 0)
        return hours

    def get_sites_req_num(self, sites: dict, new_until_time: datetime, hours: int):
        """
        sites: [{'api': 'https://x.x.1.x:44135/loki/api/v1/query', 'job': 'servicebackend'}]
        """
        _req_num = 0
        until_timestamp = int(new_until_time.timestamp())
        for site in sites:
            api = site.get('api', '')
            job = site.get('job', '')
            try:
                r_num = self.get_site_req_num(
                    api=api, job=job, until_timestamp=until_timestamp, hours=hours)
            except Exception:
                r_num = 0

            _req_num += r_num

        return _req_num

    def get_site_req_num(self, api: str, job: str, until_timestamp: int, hours: int):
        value = f'count_over_time({{job="{job}"}}[{hours}h])'
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


class LogSiteReqCounter:
    @staticmethod
    def get_now_timestamp() -> int:
        return int(datetime.utcnow().replace(second=0).timestamp())

    def __init__(self, minutes: int = 1):
        """
        :param minutes: 统计当前时间前n分钟请求数，== 定时统计周期
        """
        self.cycle_minutes = minutes

    def run(self, update_before_invalid_cycles: int = None):
        """
        :update_before_invalid_cycles: 尝试更新前n个周期的无效记录，大于0有效，默认不尝试更新前面可能无效的记录
        """
        now_timestamp = self.get_now_timestamp()
        sites_count, ok_site_ids = self.async_generate_req_num_log(now_timestamp=now_timestamp)
        ok_count = len(ok_site_ids)
        print(f'{timezone.now().isoformat(sep=" ", timespec="seconds")} End，log sites: {sites_count}, ok: {ok_count}')
        ret = {'sites_count': sites_count, 'new_ok_count': ok_count}
        if update_before_invalid_cycles and update_before_invalid_cycles > 0:
            before_minutes = self.cycle_minutes * update_before_invalid_cycles
            invalid_count, update_count, update_ok_count = self.try_update_before_invalid_records(
                before_minutes=before_minutes, now_timestamp=now_timestamp, ok_site_ids=ok_site_ids
            )
            end_time = datetime.fromtimestamp(now_timestamp).isoformat(sep=" ", timespec="seconds")
            print(f'{timezone.now().isoformat(sep=" ", timespec="seconds")} '
                  f'End，within {before_minutes} minutes before {end_time}; '
                  f'invalid: {invalid_count}, try update: {update_count}, ok: {update_ok_count}')
            ret['invalid_count'] = invalid_count
            ret['update_count'] = update_count
            ret['update_ok_count'] = update_ok_count

        return ret

    @staticmethod
    def get_log_sites():
        qs = LogSite.objects.select_related('org_data_center').all()
        return list(qs)

    def async_generate_req_num_log(self, now_timestamp: int):
        sites = self.get_log_sites()
        if not sites:
            return 0, 0

        tasks = [self.req_num_for_site(site=site, now_timestamp=now_timestamp) for site in sites]
        ok_site_ids = self.do_tasks(tasks=tasks)
        return len(sites), ok_site_ids

    def do_tasks(self, tasks: list):
        results = asyncio.run(self.do_async_requests(tasks))

        ok_site_ids = []
        for r in results:
            if isinstance(r, tuple) and len(r) == 3:
                site_id, r_num, now_timestamp = r
                if isinstance(r_num, int):
                    obj = self.create_req_num_log(timestamp=now_timestamp, log_site_id=site_id, req_num=r_num)
                    if obj:
                        ok_site_ids.append(site_id)
                else:
                    self.create_req_num_log(timestamp=now_timestamp, log_site_id=site_id, req_num=-1)
            else:
                print(r)
                continue

        return ok_site_ids

    @staticmethod
    async def do_async_requests(tasks):
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def req_num_for_site(self, site: LogSite, now_timestamp: int):
        try:
            r_num = await self.get_site_req_num(site=site, until_timestamp=now_timestamp, minutes=self.cycle_minutes)
        except Exception as exc:
            err = Exception(f'{timezone.now().isoformat(sep=" ", timespec="seconds")},{site.name},{exc}')
            return site.id, err, now_timestamp

        return site.id, r_num, now_timestamp

    @staticmethod
    async def get_site_req_num(site: LogSite, until_timestamp: int, minutes: int):
        value = f'count_over_time({{job="{site.job_tag}"}}[{minutes}m])'
        querys = {'query': value, 'time': until_timestamp}

        provider = build_loki_provider(odc=site.org_data_center)
        try:
            result = await LogLokiAPI().async_query(provider=provider, querys=querys)
        except Exception:
            result = await LogLokiAPI().async_query(provider=provider, querys=querys)

        if result:
            value = result[0]['value']
            return int(value[1])

        return 0

    @staticmethod
    def create_req_num_log(timestamp: int, log_site_id: str, req_num: int):
        try:
            obj = LogSiteTimeReqNum(timestamp=timestamp, site_id=log_site_id, count=req_num)
            obj.save(force_insert=True)
            return obj
        except Exception as e:
            print(f'Error, {str(e)}')
            return None

    def try_update_before_invalid_records(self, before_minutes: int, now_timestamp: int, ok_site_ids: list):
        """
        :before_minutes: 指定更新前多少分钟内的无效数据
        """
        start = now_timestamp - 60 * before_minutes
        objs = self.get_need_update_objs(start=start, end=now_timestamp)
        if not objs:
            return 0, 0, 0

        site_map = self.group_by_site(objs)
        down_site_ids = self.series_invalid_site_ids(
            site_map=site_map, now_ts=now_timestamp, cycle_minutes=self.cycle_minutes, ok_site_ids=ok_site_ids)

        return self.async_do_update_invalid_records(records=objs, down_site_ids=down_site_ids)

    #  -----  update invalid  ---------

    def run_update_invalid(self, before_minutes: int = 5, now_timestamp: int = None):
        """
        :before_minutes: 指定更新前多少分钟内的无效数据
        """
        if not now_timestamp:
            now_timestamp = self.get_now_timestamp()

        invalid_count, update_count, ok_count = self.async_update_invalid_records(
            now_timestamp=now_timestamp, before_minutes=before_minutes
        )
        end_time = datetime.fromtimestamp(now_timestamp).isoformat(sep=" ", timespec="seconds")
        print(f'{timezone.now().isoformat(sep=" ", timespec="seconds")} '
              f'End，within {before_minutes} minutes before {end_time}; '
              f'invalid: {invalid_count}, try update: {update_count}, ok: {ok_count}')
        return invalid_count, update_count, ok_count

    def async_update_invalid_records(self, now_timestamp: int, before_minutes: int = 5):
        start = now_timestamp - 60 * before_minutes
        objs = self.get_need_update_objs(start=start, end=now_timestamp)
        if not objs:
            return 0, 0, 0

        site_map = self.group_by_site(objs)
        down_site_ids = self.service_down_sites(
            site_map=site_map, before_minutes=before_minutes, cycle_minutes=self.cycle_minutes, now_ts=now_timestamp)

        return self.async_do_update_invalid_records(records=objs, down_site_ids=down_site_ids)

    def async_do_update_invalid_records(self, records, down_site_ids: list):
        ok_count = 0
        update_count = 0
        tasks = []
        for obj in records:
            if obj.count >= 0:
                continue

            try:
                site_id = obj.site.id
            except Exception as exc:
                continue

            if site_id not in down_site_ids:
                tasks.append(self.req_num_for_invalid_obj(obj=obj))

            if len(tasks) >= 100:
                ok_ct = self.do_update_tasks(tasks=tasks)
                update_count += len(tasks)
                ok_count += ok_ct
                tasks = []

        # 最后一部分
        if tasks:
            ok_ct = self.do_update_tasks(tasks=tasks)
            update_count += len(tasks)
            ok_count += ok_ct

        return len(records), update_count, ok_count

    async def req_num_for_invalid_obj(self, obj: LogSiteTimeReqNum):
        site: LogSite = obj.site
        try:
            r_num = await self.get_site_req_num(site=site, until_timestamp=obj.timestamp, minutes=self.cycle_minutes)
        except Exception as exc:
            err = Exception(f'{timezone.now().isoformat(sep=" ", timespec="seconds")},{site.name},{exc}')
            return obj, err

        return obj, r_num

    def do_update_tasks(self, tasks: list):
        results = asyncio.run(self.do_async_requests(tasks))

        ok_count = 0
        update_objs = []
        for r in results:
            if isinstance(r, tuple) and len(r) == 2:
                obj, r_num = r
                if isinstance(r_num, int):
                    obj.count = r_num
                    update_objs.append(obj)
            else:
                print(r)
                continue

        if update_objs:
            try:
                ok_count = LogSiteTimeReqNum.objects.bulk_update(update_objs, fields=['count'])
            except Exception as exc:
                pass

        return ok_count

    @staticmethod
    def get_need_update_objs(start: int, end: int, log_site_id=None):
        qs = LogSiteTimeReqNum.objects.select_related('site').filter(
            timestamp__gte=start, timestamp__lte=end, count__lt=0)
        if log_site_id:
            qs = qs.filter(site__id=log_site_id)

        return qs.order_by('timestamp')

    @staticmethod
    def group_by_site(qs):
        d = {}
        for obj in qs:
            site_id = obj.site_id
            if site_id not in d:
                d[site_id] = [obj]
            else:
                d[site_id].append(obj)

        return d

    @staticmethod
    def service_down_sites(site_map: dict, before_minutes: int, cycle_minutes: int, now_ts: int):
        """
        数据提供者服务可能无法访问的日志单元
        """
        count = before_minutes // cycle_minutes
        down_site_ids = []
        for site_id, objs in site_map.items():
            tss = [i.timestamp for i in objs if i.count < 0]

            down = LogSiteReqCounter.is_site_service_down(
                tss=tss, ts_count=count, cycle_minutes=cycle_minutes, now_ts=now_ts
            )
            if down:
                down_site_ids.append(site_id)

        return down_site_ids

    @staticmethod
    def is_site_service_down(tss: List[int], ts_count: int, cycle_minutes: int, now_ts: int):
        """
        判定数据提供者服务是否无法访问

        :param tss: 无效记录的时间戳list
        :param ts_count: 查询无效记录的时间段内理论上总数据量
        :param cycle_minutes: 时序统计记录的周期
        :param now_ts: 当前时间戳
        :return:
            True    # down
            False   # not down
        """
        min_times = 3
        tss_len = len(tss)
        # 无效记录数少，不考虑是否无法访问
        if tss_len <= min_times:
            return False

        # 几乎全部无效，基本判定无法访问
        if tss_len >= (ts_count - min_times):
            return True

        # 相邻时间戳差值
        tss.sort()
        diff_l = [tss[i + 1] - tss[i] for i in range(tss_len - 1) if tss[i + 1] != tss[i]]

        series_limit = 60 * cycle_minutes + 1  # 连续判定界限值，统计周期秒数+1
        # 临近几个周期是否连续无效
        recent_series_invalid = LogSiteReqCounter.is_recent_series_invalid(
            now_ts=now_ts, invalid_last_ts=tss[-1], ts_diff_l=diff_l[-min_times:],
            series_limit=series_limit, last_series_limit=60 * cycle_minutes * 2
        )

        invalid_ratio = (len(diff_l) + 1) * 100 // ts_count

        if invalid_ratio >= 95:  # 无效记录占比很大，基本判定服务无法访问
            return True
        else:
            # 时间戳连续无效记录总数，时间戳连续无效记录赞比
            series_count = sum(i <= series_limit for i in diff_l)
            series_ratio = series_count * 100 // len(diff_l)
            if invalid_ratio >= 50:   # 无效记录占比较大
                if recent_series_invalid and series_ratio >= 50:  # 临近几个周期无效，连续无效占比较大
                    return True
            elif invalid_ratio >= 30:
                if recent_series_invalid and series_ratio >= 90:  # 临近几个周期无效，连续无效占比很大
                    return True
            elif invalid_ratio >= 10:
                if recent_series_invalid and series_ratio >= 95:  # 临近几个周期无效，连续无效占比很大
                    return True
            else:   # 无效记录占比较小
                return False

        return False

    @staticmethod
    def is_recent_series_invalid(
            now_ts: int, invalid_last_ts: int, ts_diff_l: list,
            series_limit: int, last_series_limit: int = None
    ):
        """
        是否最近几个周期连续无效（查询失败）

        :param now_ts: 当前时间戳
        :param invalid_last_ts: 最近的一次无效时间戳
        :param ts_diff_l: 时间戳相邻差值列表
        :param series_limit: 相邻差值在此值内 判定为连续
        :param last_series_limit: 最近的一次无效时间戳 invalid_last_ts 与 当前时间戳 now_ts 差值在此值内 判定为连续，
                                  默认为series_limit
        """
        if last_series_limit is None:
            last_series_limit = series_limit

        recent_series_invalid = False
        if (now_ts - invalid_last_ts) <= last_series_limit:  # 最后一次无效记录在两个周期内就判定和当前周期时间戳连续
            recent_series = ts_diff_l
            recent_series_count = sum(i <= series_limit for i in recent_series)
            if recent_series_count == len(recent_series):  # 最近连续几个周期数据都无效（查询失败）
                recent_series_invalid = True

        return recent_series_invalid

    @staticmethod
    def is_series_invalid(tss: List[int], cycle_minutes: int, now_ts: int):
        """
        是否所有周期连续无效（查询失败），判定数据提供者服务是否无法访问

        :param tss: 无效记录的时间戳list
        :param cycle_minutes: 时序统计记录的周期
        :param now_ts: 当前时间戳
        :return:
            True    # down
            False   # not down
        """
        if len(tss) <= 1:
            return False

        # 相邻时间戳差值
        tss.sort()
        diff_l = [tss[i + 1] - tss[i] for i in range(len(tss) - 1) if tss[i + 1] != tss[i]]

        series_limit = 60 * cycle_minutes + 1  # 连续判定界限值，统计周期秒数+1
        # 临近几个周期是否连续无效
        recent_series_invalid = LogSiteReqCounter.is_recent_series_invalid(
            now_ts=now_ts, invalid_last_ts=tss[-1], ts_diff_l=diff_l, series_limit=series_limit
        )
        return recent_series_invalid

    @staticmethod
    def series_invalid_site_ids(site_map: dict, cycle_minutes: int, now_ts: int, ok_site_ids: list):
        """
        全部连续无效日志单元
        """
        down_site_ids = []
        for site_id, objs in site_map.items():
            if ok_site_ids and site_id in ok_site_ids:
                continue

            tss = [i.timestamp for i in objs if i.count < 0]
            down = LogSiteReqCounter.is_series_invalid(
                tss=tss, cycle_minutes=cycle_minutes, now_ts=now_ts
            )
            if down:
                down_site_ids.append(site_id)

        return down_site_ids
