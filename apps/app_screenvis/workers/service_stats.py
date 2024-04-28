import asyncio
from typing import List
from datetime import datetime

from django.utils import timezone as dj_timezone
import aiohttp

from apps.app_screenvis.models import ServerService, BaseService, ServerServiceTimedStats, VPNTimedStats


class ServerServiceStatsWorker:
    @staticmethod
    def get_now_timestamp() -> int:
        return int(datetime.utcnow().replace(second=0).timestamp())

    def __init__(self, minutes: int = 10):
        """
        :param minutes: 查询服务单元统计数据，== 定时周期
        """
        self.cycle_minutes = minutes

    def run(self, now_timestamp: int = None):
        if not now_timestamp:
            now_timestamp = self.get_now_timestamp()

        units_count, ok_unit_ids, compute_objs, vpn_objs = self.async_generate_stats(now_timestamp=now_timestamp)
        ok_count = len(ok_unit_ids)
        print(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")} End，'
              f'service units: {units_count}, ok: {ok_count}, compute: {len(compute_objs)}, vpn: {len(vpn_objs)}')
        return {
            'unit_count': units_count,
            'new_ok_count': ok_count,
            'compute_count': len(compute_objs),
            'vpn_count': len(vpn_objs)
        }

    @staticmethod
    def get_service_units() -> List[BaseService]:
        qs = ServerService.objects.filter(status=ServerService.Status.ENABLE.value)
        return list(qs)

    def async_generate_stats(self, now_timestamp: int):
        units = self.get_service_units()
        if not units:
            return 0, [], [], []

        tasks = [self.req_stats_for_unit(unit=unit, now_timestamp=now_timestamp) for unit in units]
        ok_unit_ids, compute_objs, vpn_objs = self.do_tasks(tasks=tasks)
        return len(units), ok_unit_ids, compute_objs, vpn_objs

    def do_tasks(self, tasks: list):
        results = asyncio.run(self.do_async_requests(tasks))

        ok_unit_ids = []
        compute_objs = []
        vpn_objs = []
        unit_err_map = {}
        for r in results:
            if isinstance(r, tuple) and len(r) == 3:
                unit_id, r_value, now_timestamp = r
                if isinstance(r_value, dict):
                    ok_unit_ids.append(unit_id)
                    compute_objs.append(
                        self.build_compute_stats_obj(unit_id=unit_id, now_ts=now_timestamp, data=r_value))
                    vpn_objs.append(
                        self.build_vpn_stats_obj(unit_id=unit_id, now_ts=now_timestamp, data=r_value))
                else:
                    unit_err_map[unit_id] = r_value
            else:
                print(r)
                continue

        if compute_objs:
            try:
                compute_objs = ServerServiceTimedStats.objects.bulk_create(objs=compute_objs, batch_size=200)
            except Exception as exc:
                unit_err_map['server_bulk_create'] = exc

        if vpn_objs:
            try:
                vpn_objs = VPNTimedStats.objects.bulk_create(objs=vpn_objs, batch_size=200)
            except Exception as exc:
                unit_err_map['vpn_bulk_create'] = exc

        try:
            for err in unit_err_map.values():
                print(err)
        except Exception as exc:
            pass

        return ok_unit_ids, compute_objs, vpn_objs

    @staticmethod
    def build_compute_stats_obj(unit_id: int, now_ts: int, data: dict) -> ServerServiceTimedStats:
        mem_total = data['mem_total']
        mem_allocated = data['mem_allocated']
        mem_unit = data.get('mem_unit', '')
        if str(mem_unit).lower() in ['mb', 'mib']:
            mem_total = mem_total / 1024
            mem_allocated = mem_allocated / 1024

        obj = ServerServiceTimedStats(
            service_id=unit_id, timestamp=now_ts,
            server_count=int(data['vm_created']),
            disk_count=int(data['vdisk_num']),
            ip_count=int(data['ips_total']),
            ip_used_count=int(data['ips_used']),
            mem_size=int(mem_total),
            mem_used_size=int(mem_allocated),
            cpu_count=int(data['vcpu_total']),
            cpu_used_count=int(data['vcpu_allocated'])
        )
        obj.enforce_id()
        return obj

    @staticmethod
    def build_vpn_stats_obj(unit_id: int, now_ts: int, data: dict) -> VPNTimedStats:
        obj = VPNTimedStats(
            service_id=unit_id, timestamp=now_ts,
            vpn_online_count=int(data.get('vpn_online', 0)),
            vpn_active_count=int(data['vpn_active']),
            vpn_count=int(data['vpn_total'])
        )
        obj.enforce_id()
        return obj

    @staticmethod
    async def do_async_requests(tasks):
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def req_stats_for_unit(self, unit: BaseService, now_timestamp: int):
        try:
            r_value = await self.get_unit_stats_data(unit=unit)
        except Exception as exc:
            err = Exception(f'{dj_timezone.now().isoformat(sep=" ", timespec="seconds")},{unit.name},{exc}')
            return unit.id, err, now_timestamp

        return unit.id, r_value, now_timestamp

    async def get_unit_stats_data(self, unit: BaseService):
        host = unit.endpoint_url.rstrip('/')
        api_url = f'{host}/api/v3/compute/quota/center?mem_unit=GB'

        try:
            result = await self.async_request(api_url=api_url, username=unit.username, password=unit.raw_password())
        except Exception:
            result = await self.async_request(api_url=api_url, username=unit.username, password=unit.raw_password())

        return result['quota']

    @staticmethod
    async def async_request(api_url: str, username: str, password: str):
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.get(
                    url=api_url,
                    auth=aiohttp.BasicAuth(login=username, password=password),
                    timeout=aiohttp.ClientTimeout(connect=5, total=30))
        except aiohttp.ClientConnectionError:
            raise Exception('api request timeout')
        except aiohttp.ClientError as exc:
            raise Exception(f'api request error; {str(exc)}')

        status_code = r.status
        if 300 > status_code >= 200:
            data = await r.json()
            return data

        try:
            data = await r.json()
            err_code = data.get('err_code')
            msg = f"status: {status_code}, err_code: {err_code}, error: {data.get('code_text')}"
        except Exception as e:
            text = await r.text()
            msg = f"status: {status_code}, error: {text}"

        raise Exception(msg)
