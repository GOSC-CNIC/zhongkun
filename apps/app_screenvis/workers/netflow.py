import asyncio
from typing import List, Tuple, Union
from datetime import datetime
from collections import namedtuple

from django.utils import timezone as dj_timezone

from apps.app_screenvis.models import MetricMonitorUnit, HostNetflow
from apps.app_screenvis.utils import build_metric_provider, MetricProvider
from apps.app_screenvis.backends import MetricQueryAPI


NetFlowValue = namedtuple('NetFlowValue', ['ts', 'in_val', 'out_val'])


class HostNetflowWorker:
    @staticmethod
    def get_now_timestamp() -> int:
        return int(datetime.utcnow().replace(second=0).timestamp())

    def __init__(self, minutes: int = 3):
        """
        :param minutes: 统计当前时间前n分钟cpu使用率，== 定时统计周期
        """
        self.cycle_minutes = minutes

    def run(self, now_timestamp: int = None):
        if not now_timestamp:
            now_timestamp = self.get_now_timestamp()

        units_count, ok_unit_ids, objs = self.async_generate_netflow(now_timestamp=now_timestamp)
        ok_count = len(ok_unit_ids)
        print(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")} End，'
              f'host units: {units_count}, ok: {ok_count}')
        ret = {'units_count': units_count, 'new_ok_count': ok_count}

        fill_ret = self.try_fill_before_miss_records(now_timestamp=now_timestamp)
        print(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")}, End try fill miss data')
        for s in fill_ret:
            print(s)

        return ret

    @staticmethod
    def get_host_metric_units():
        qs = MetricMonitorUnit.objects.filter(
            unit_type__in=[MetricMonitorUnit.UnitType.HOST.value, MetricMonitorUnit.UnitType.VM.value])
        return list(qs)

    def async_generate_netflow(self, now_timestamp: int):
        units = self.get_host_metric_units()
        if not units:
            return 0, [], []

        provider = build_metric_provider()
        tasks = [self.req_netflow_for_unit(unit=unit, now_timestamp=now_timestamp, provider=provider) for unit in units]
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

    async def req_netflow_for_unit(self, unit: MetricMonitorUnit, now_timestamp: int, provider: MetricProvider):
        try:
            r_value = await self.get_unit_netflow_values(
                unit=unit, until_timestamp=now_timestamp, minutes=self.cycle_minutes, provider=provider)
        except Exception as exc:
            err = Exception(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")},{unit.name},{exc}')
            return unit.id, err, now_timestamp

        return unit.id, r_value, now_timestamp

    async def get_unit_netflow_values(
            self, unit: MetricMonitorUnit, until_timestamp: int, minutes: int, provider: MetricProvider
    ) -> Tuple[float, float]:
        minutes = min(minutes, 5)
        flow_in = await self.get_unit_netflow_in_value(
            unit=unit, until_timestamp=until_timestamp, minutes=minutes, endpoint_url=provider.endpoint_url)
        flow_out = await self.get_unit_netflow_out_value(
            unit=unit, until_timestamp=until_timestamp, minutes=minutes, endpoint_url=provider.endpoint_url)

        return flow_in, flow_out

    @staticmethod
    async def get_unit_netflow_in_value(
            unit: MetricMonitorUnit, until_timestamp: int, minutes: int, endpoint_url: str
    ) -> float:
        query = f'sum(rate(node_network_receive_bytes_total{{job="{unit.job_tag}", device!="lo"}}[{minutes}m]))'
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
        query = f'sum(rate(node_network_transmit_bytes_total{{job="{unit.job_tag}", device!="lo"}}[{minutes}m]))'
        querys = {'query': query, 'time': until_timestamp}

        try:
            result = await MetricQueryAPI().async_raw_query(endpoint_url=endpoint_url, querys=querys)
        except Exception:
            result = await MetricQueryAPI().async_raw_query(endpoint_url=endpoint_url, querys=querys)

        if result:
            value = result[0]['value']
            return float(value[1])

        return 0

    #  -----  fill miss  ---------

    def try_fill_before_miss_records(self, now_timestamp: int) -> List[str]:
        """
        检查前面时间段是否缺少时序数据，需要填充
        """
        cycle_seconds = 60 * self.cycle_minutes
        end_ts = now_timestamp - cycle_seconds  # 当前周期不需要补
        units = self.get_host_metric_units()
        ret = []
        for unit in units:
            last_objs = self.get_unit_last_objs(unit_id=unit.id, limit=3)
            # 需补前24小时内数据
            if len(last_objs) < 3:
                fill_start_ts = now_timestamp - 60 * 60 * 24
                need_fill = True
            else:
                need_fill, fill_start_ts = self.get_fill_start_ts(
                    objs=last_objs, cycle_minutes=self.cycle_minutes, now_ts=now_timestamp)
                fill_start_ts += cycle_seconds  # 下一个周期时间戳开始

            if not need_fill:
                continue

            fill_count = self.fill_data_for_unit(unit=unit, start_ts=fill_start_ts, end_ts=end_ts)
            ret.append(f'{unit.name}, time range {fill_start_ts} - {end_ts}, '
                       f'{end_ts - fill_start_ts}s, fill {fill_count} data')

        return ret

    def fill_data_for_unit(self, unit: MetricMonitorUnit, start_ts: int, end_ts: int):
        cycle_minutes = self.cycle_minutes
        provider = build_metric_provider()
        tasks = [
            self.req_range_values_for_unit(
                unit=unit, start_ts=start_ts, end_ts=end_ts,
                provider=provider, cycle_minutes=cycle_minutes
            )
        ]
        results = asyncio.run(self.do_async_requests(tasks))
        fill_count = 0
        for r in results:
            if isinstance(r, tuple) and len(r) == 3:
                ok, unit_id, r_values = r
                if ok and r_values:
                    objs = []
                    for item in r_values:
                        ob = HostNetflow(
                            timestamp=item.ts, flow_in=item.in_val, flow_out=item.out_val, unit=unit
                        )
                        ob.enforce_id()
                        objs.append(ob)

                    if objs:
                        objs = HostNetflow.objects.bulk_create(objs)
                        fill_count = len(objs)
            else:
                print(r)
                continue

        return fill_count

    @staticmethod
    async def get_unit_netflow_in_value_range(
            unit: MetricMonitorUnit, start_ts: int, end_ts: int, step: int, endpoint_url: str
    ) -> List[NetFlowValue]:
        query = f'sum(rate(node_network_receive_bytes_total{{job="{unit.job_tag}", device!="lo"}}[2m]))'
        querys = {'query': query, 'start': start_ts, 'end': end_ts, 'step': step}
        try:
            result = await MetricQueryAPI().async_raw_query_range(endpoint_url=endpoint_url, querys=querys)
        except Exception:
            result = await MetricQueryAPI().async_raw_query_range(endpoint_url=endpoint_url, querys=querys)

        if result:
            values = result[0]['values']
            return [NetFlowValue(ts=int(float(item[0])), in_val=float(item[1]), out_val=0) for item in values]

        return []

    @staticmethod
    async def get_unit_netflow_out_value_range(
            unit: MetricMonitorUnit, start_ts: int, end_ts: int, step: int, endpoint_url: str
    ) -> List[NetFlowValue]:
        query = f'sum(rate(node_network_transmit_bytes_total{{job="{unit.job_tag}", device!="lo"}}[2m]))'
        querys = {'query': query, 'start': start_ts, 'end': end_ts, 'step': step}
        try:
            result = await MetricQueryAPI().async_raw_query_range(endpoint_url=endpoint_url, querys=querys)
        except Exception:
            result = await MetricQueryAPI().async_raw_query_range(endpoint_url=endpoint_url, querys=querys)

        if result:
            values = result[0]['values']
            return [NetFlowValue(ts=int(float(item[0])), in_val=0, out_val=float(item[1])) for item in values]

        return []

    async def get_unit_netflow_range_values(
            self, unit: MetricMonitorUnit, start_ts: int, end_ts: int, minutes: int, provider: MetricProvider
    ) -> List[NetFlowValue]:
        step = 60 * minutes
        flow_in_values = await self.get_unit_netflow_in_value_range(
            unit=unit, start_ts=start_ts, end_ts=end_ts, step=step, endpoint_url=provider.endpoint_url)
        flow_out_values = await self.get_unit_netflow_out_value_range(
            unit=unit, start_ts=start_ts, end_ts=end_ts, step=step, endpoint_url=provider.endpoint_url)

        values = []
        if flow_in_values and flow_out_values:
            values = self.piece_together_in_out_values(flow_in_values=flow_in_values, flow_out_values=flow_out_values)

        return values

    @staticmethod
    def piece_together_in_out_values(
            flow_in_values: List[NetFlowValue], flow_out_values: List[NetFlowValue]
    ) -> List[NetFlowValue]:
        """
        进、出流量时序数据数组按时间戳拼合
        """
        piece_values = []
        flow_in_values.sort(key=lambda v: v.ts, reverse=False)
        flow_out_values.sort(key=lambda v: v.ts, reverse=False)
        max_len = min(len(flow_in_values), len(flow_out_values))
        for x in range(max_len):
            in_item = flow_in_values.pop(0)
            out_item = flow_out_values.pop(0)
            piece_values.append(NetFlowValue(ts=in_item.ts, in_val=in_item.in_val, out_val=out_item.out_val))

        if flow_in_values:
            piece_values += flow_in_values
        else:
            piece_values += flow_out_values

        return piece_values

    async def req_range_values_for_unit(
            self, unit: MetricMonitorUnit, start_ts: int, end_ts: int, provider: MetricProvider, cycle_minutes: int
    ) -> Tuple[bool, str, Union[List[NetFlowValue], Exception]]:
        try:
            r_values = await self.get_unit_netflow_range_values(
                unit=unit, start_ts=start_ts, end_ts=end_ts, minutes=cycle_minutes, provider=provider)
        except Exception as exc:
            err = Exception(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")},{unit.name},{exc}')
            return False, unit.id, err

        return True, unit.id, r_values

    @staticmethod
    def get_fill_start_ts(
            objs: list[HostNetflow], cycle_minutes: int, now_ts: int) -> Tuple[bool, int]:
        """
        是否有时序数据缺失，并返回缺失时序数据的开始时间戳
        """
        fill_start_ts = 0
        pre_ts = now_ts
        objs.sort(key=lambda x: x.timestamp, reverse=True)
        for o in objs:
            o_ts = o.timestamp
            # 超过2个时序数据周期，中间需要补数据
            if abs(pre_ts - o_ts) > 60 * cycle_minutes * 2:
                fill_start_ts = o_ts

            pre_ts = o_ts

        if fill_start_ts <= 0:
            return False, fill_start_ts

        return True, fill_start_ts

    @staticmethod
    def get_unit_last_objs(unit_id, limit: int) -> List:
        qs = HostNetflow.objects.filter(unit_id=unit_id).order_by('-timestamp')[0:limit]
        return list(qs)
