import asyncio
from typing import List, Tuple
from datetime import datetime

from django.utils import timezone as dj_timezone

from apps.app_screenvis.models import MetricMonitorUnit, HostNetflow
from apps.app_screenvis.utils import build_metric_provider
from apps.app_screenvis.backends import MetricQueryAPI


class HostNetflowWorker:
    @staticmethod
    def get_now_timestamp() -> int:
        return int(datetime.utcnow().replace(second=0).timestamp())

    def __init__(self, minutes: int = 3):
        """
        :param minutes: 统计当前时间前n分钟cpu使用率，== 定时统计周期
        """
        self.cycle_minutes = minutes

    def run(self, update_before_invalid_cycles: int = None, now_timestamp: int = None):
        """
        :update_before_invalid_cycles: 尝试更新前n个周期的无效记录，大于0有效，默认不尝试更新前面可能无效的记录
        """
        if not now_timestamp:
            now_timestamp = self.get_now_timestamp()

        units_count, ok_unit_ids, objs = self.async_generate_netflow(now_timestamp=now_timestamp)
        ok_count = len(ok_unit_ids)
        print(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")} End，'
              f'host units: {units_count}, ok: {ok_count}')
        ret = {'units_count': units_count, 'new_ok_count': ok_count}
        if update_before_invalid_cycles and update_before_invalid_cycles > 0:
            before_minutes = self.cycle_minutes * update_before_invalid_cycles
            invalid_count, update_count, update_ok_count = self.try_update_before_invalid_records(
                before_minutes=before_minutes, now_timestamp=now_timestamp, ok_unit_ids=ok_unit_ids
            )
            end_time = datetime.fromtimestamp(now_timestamp).isoformat(sep=" ", timespec="seconds")
            print(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")} '
                  f'End，within {before_minutes} minutes before {end_time}; '
                  f'invalid: {invalid_count}, try update: {update_count}, ok: {update_ok_count}')
            ret['invalid_count'] = invalid_count
            ret['update_count'] = update_count
            ret['update_ok_count'] = update_ok_count

        return ret

    @staticmethod
    def get_host_metric_units():
        qs = MetricMonitorUnit.objects.select_related(
            'data_center').filter(unit_type=MetricMonitorUnit.UnitType.HOST.value)
        return list(qs)

    def async_generate_netflow(self, now_timestamp: int):
        units = self.get_host_metric_units()
        if not units:
            return 0, [], []

        tasks = [self.req_netflow_for_unit(unit=unit, now_timestamp=now_timestamp) for unit in units]
        ok_unit_ids, objs = self.do_tasks(tasks=tasks)
        return len(units), ok_unit_ids, objs

    def do_tasks(self, tasks: list):
        results = asyncio.run(self.do_async_requests(tasks))

        ok_unit_ids = []
        objs = []
        for r in results:
            if isinstance(r, tuple) and len(r) == 3:
                unit_id, r_values, now_timestamp = r
                if isinstance(r_values, tuple) and len(r_values) == 2:
                    ok_unit_ids.append(unit_id)
                    flow_in, flow_out = r_values
                else:
                    flow_in = flow_out = -1

                obj = HostNetflow(timestamp=now_timestamp, unit_id=unit_id, flow_in=flow_in, flow_out=flow_out)
                obj.enforce_id()    # 生成填充id，批量插入不调用save方法
                objs.append(obj)
            else:
                print(r)
                continue

        if objs:
            try:
                objs = HostNetflow.objects.bulk_create(objs=objs, batch_size=200)
            except Exception as exc:
                pass

        return ok_unit_ids, objs

    @staticmethod
    async def do_async_requests(tasks):
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def req_netflow_for_unit(self, unit: MetricMonitorUnit, now_timestamp: int):
        try:
            r_value = await self.get_unit_netflow_values(
                unit=unit, until_timestamp=now_timestamp, minutes=self.cycle_minutes)
        except Exception as exc:
            err = Exception(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")},{unit.name},{exc}')
            return unit.id, err, now_timestamp

        return unit.id, r_value, now_timestamp

    async def get_unit_netflow_values(
            self, unit: MetricMonitorUnit, until_timestamp: int, minutes: int
    ) -> Tuple[float, float]:
        minutes = min(minutes, 5)
        provider = build_metric_provider(odc=unit.data_center)
        flow_in = await self.get_unit_netflow_in_value(
            unit=unit, until_timestamp=until_timestamp, minutes=minutes, endpoint_url=provider.endpoint_url)
        flow_out = await self.get_unit_netflow_out_value(
            unit=unit, until_timestamp=until_timestamp, minutes=minutes, endpoint_url=provider.endpoint_url)

        return flow_in, flow_out

    @staticmethod
    async def get_unit_netflow_in_value(
            unit: MetricMonitorUnit, until_timestamp: int, minutes: int, endpoint_url: str
    ) -> float:
        query = f'sum(rate(node_network_receive_bytes_total{{job="{unit.job_tag}", device!~"lo|br_.*|vnet.*"}}' \
                f'[{minutes}m]) * on(job, instance, device) (node_network_info{{operstate="up"}} == 1))'
        querys = {'query': query, 'time': until_timestamp}
        try:
            result = await MetricQueryAPI().async_raw_query(endpoint_url=endpoint_url, querys=querys)
        except Exception:
            result = await MetricQueryAPI().async_raw_query(endpoint_url=endpoint_url, querys=querys)

        if result:
            value = result[0]['value']
            return float(value[1])

        return 0

    @staticmethod
    async def get_unit_netflow_out_value(
            unit: MetricMonitorUnit, until_timestamp: int, minutes: int, endpoint_url: str
    ) -> float:
        query = f'sum(rate(node_network_transmit_bytes_total{{job="{unit.job_tag}", device!~"lo|br_.*|vnet.*"}}' \
                f'[{minutes}m]) * on(job, instance, device) (node_network_info{{operstate="up"}} == 1))'
        querys = {'query': query, 'time': until_timestamp}

        try:
            result = await MetricQueryAPI().async_raw_query(endpoint_url=endpoint_url, querys=querys)
        except Exception:
            result = await MetricQueryAPI().async_raw_query(endpoint_url=endpoint_url, querys=querys)

        if result:
            value = result[0]['value']
            return float(value[1])

        return 0

    def try_update_before_invalid_records(self, before_minutes: int, now_timestamp: int, ok_unit_ids: list):
        """
        :before_minutes: 指定更新前多少分钟内的无效数据
        """
        start = now_timestamp - 60 * before_minutes
        objs = self.get_need_update_objs(start=start, end=now_timestamp)
        if not objs:
            return 0, 0, 0

        unit_objs_map = self.group_by_unit(objs)
        down_site_ids = self.series_invalid_unit_ids(
            unit_objs_map=unit_objs_map, now_ts=now_timestamp,
            cycle_minutes=self.cycle_minutes, ok_unit_ids=ok_unit_ids
        )

        return self.async_do_update_invalid_records(records=objs, down_unit_ids=down_site_ids)

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
        print(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")} '
              f'End，within {before_minutes} minutes before {end_time}; '
              f'invalid: {invalid_count}, try update: {update_count}, ok: {ok_count}')
        return invalid_count, update_count, ok_count

    def async_update_invalid_records(self, now_timestamp: int, before_minutes: int = 5):
        start = now_timestamp - 60 * before_minutes
        objs = self.get_need_update_objs(start=start, end=now_timestamp)
        if not objs:
            return 0, 0, 0

        unit_objs_map = self.group_by_unit(objs)
        down_unit_ids = self.service_down_unit_ids(
            unit_objs_map=unit_objs_map, before_minutes=before_minutes,
            cycle_minutes=self.cycle_minutes, now_ts=now_timestamp
        )

        return self.async_do_update_invalid_records(records=objs, down_unit_ids=down_unit_ids)

    def async_do_update_invalid_records(self, records, down_unit_ids: list):
        ok_count = 0
        update_count = 0
        tasks = []
        for obj in records:
            if obj.flow_in >= 0 and obj.flow_out >= 0:
                continue

            try:
                unit_id = obj.unit.id
                dc = obj.unit.data_center  # 防止后续在异步执行中，从数据库同步加载dc，django报错
            except Exception as exc:
                continue

            if unit_id not in down_unit_ids:
                tasks.append(self.query_netflow_for_invalid_obj(obj=obj))

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

    async def query_netflow_for_invalid_obj(self, obj: HostNetflow):
        unit = obj.unit
        try:
            r_values = await self.get_unit_netflow_values(
                unit=unit, until_timestamp=obj.timestamp, minutes=self.cycle_minutes)
        except Exception as exc:
            err = Exception(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")},{unit.name},{exc}')
            return obj, err

        return obj, r_values

    def do_update_tasks(self, tasks: list):
        results = asyncio.run(self.do_async_requests(tasks))

        ok_count = 0
        update_objs = []
        unit_err_map = {}
        for r in results:
            if isinstance(r, tuple) and len(r) == 2:
                obj, r_values = r
                if isinstance(r_values, tuple) and len(r_values) == 2:
                    flow_in, flow_out = r_values
                    obj.flow_in = flow_in
                    obj.flow_out = flow_out
                    update_objs.append(obj)
                else:
                    unit_err_map[obj.unit_id] = r_values
            else:
                print(r)
                continue

        if update_objs:
            try:
                ok_count = HostNetflow.objects.bulk_update(update_objs, fields=['flow_in', 'flow_out'])
            except Exception as exc:
                pass

        try:
            for err in unit_err_map.values():
                print(err)
        except Exception as exc:
            pass

        return ok_count

    @staticmethod
    def get_need_update_objs(start: int, end: int, unit_id=None):
        qs = HostNetflow.objects.select_related('unit__data_center').filter(
            timestamp__gte=start, timestamp__lte=end, flow_in__lt=0)
        if unit_id:
            qs = qs.filter(unit_id=unit_id)

        return qs.order_by('timestamp')

    @staticmethod
    def group_by_unit(qs):
        d = {}
        for obj in qs:
            unit_id = obj.unit_id
            if unit_id not in d:
                d[unit_id] = [obj]
            else:
                d[unit_id].append(obj)

        return d

    def service_down_unit_ids(self, unit_objs_map: dict, before_minutes: int, cycle_minutes: int, now_ts: int):
        """
        数据提供者服务可能无法访问的指标单元
        """
        count = before_minutes // cycle_minutes
        down_unit_ids = []
        for unit_id, objs in unit_objs_map.items():
            tss = [i.timestamp for i in objs if i.flow_in < 0]

            down = self.is_unit_service_down(
                tss=tss, ts_count=count, cycle_minutes=cycle_minutes, now_ts=now_ts
            )
            if down:
                down_unit_ids.append(unit_id)

        return down_unit_ids

    def is_unit_service_down(self, tss: List[int], ts_count: int, cycle_minutes: int, now_ts: int):
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
        recent_series_invalid = self.is_recent_series_invalid(
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

    def is_series_invalid(self, tss: List[int], cycle_minutes: int, now_ts: int):
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
        recent_series_invalid = self.is_recent_series_invalid(
            now_ts=now_ts, invalid_last_ts=tss[-1], ts_diff_l=diff_l, series_limit=series_limit
        )
        return recent_series_invalid

    def series_invalid_unit_ids(self, unit_objs_map: dict, cycle_minutes: int, now_ts: int, ok_unit_ids: list):
        """
        全部连续无效日志单元
        """
        down_site_ids = []
        for site_id, objs in unit_objs_map.items():
            if ok_unit_ids and site_id in ok_unit_ids:
                continue

            tss = [i.timestamp for i in objs if i.flow_in < 0]
            down = self.is_series_invalid(
                tss=tss, cycle_minutes=cycle_minutes, now_ts=now_ts
            )
            if down:
                down_site_ids.append(site_id)

        return down_site_ids
