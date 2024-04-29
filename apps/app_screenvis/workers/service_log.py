from typing import List, Union
from datetime import datetime, timedelta, timezone
from urllib import parse

import requests
from django.utils import timezone as dj_timezone

from apps.app_screenvis.models import ServerService, ObjectService, BaseService, ServerServiceLog, ObjectServiceLog


class BaseSynchronizer:
    """
    服务单元操作日志同步器
    """
    @staticmethod
    def get_service_units() -> List[BaseService]:
        """
        查询服务单元
        """
        raise NotImplementedError('子类必须实现方法get_service_units')

    @staticmethod
    def build_log_url(endpoint_url: str, timestamp: float):
        """
        数据按时间正序查询
        """
        raise NotImplementedError('子类必须实现方法build_log_url')

    def query_page_data(self, unit: BaseService, timestamp: float) -> list:
        url = self.build_log_url(endpoint_url=unit.endpoint_url, timestamp=timestamp)
        req = requests.get(url, auth=(unit.username, unit.raw_password()))
        if req.status_code != 200:
            raise Exception(f'服务单元“{unit.name}”请求错误：{req.text}, url {url}')

        return req.json()['results']

    def get_unit_start_timestamp(self, unit_id: int) -> Union[float, None]:
        """
        获取服务单元开始同步时间戳
        """
        raise NotImplementedError('子类必须实现方法get_unit_start_timestamp')

    @staticmethod
    def build_log_model_obj(log_data: dict, unit_id: int):
        raise NotImplementedError('子类必须实现方法build_log_model_obj')

    def do_sync_units_log(self):
        units = self.get_service_units()
        err_units = []
        for unit in units:
            timestamp = self.get_unit_start_timestamp(unit_id=unit.id)
            if not timestamp:
                timestamp = (dj_timezone.now() - timedelta(days=1)).timestamp()  # 没有数据，从一天前开始同步日志

            ret = self.sync_unit_logs_from_ts(unit=unit, timestamp=timestamp)
            if ret:
                err_units.append(unit)

        return units, err_units

    def sync_unit_logs_from_ts(self, unit: BaseService, timestamp: float):
        """
        从指定时间戳开始同步服务单元的日志
        """
        return_err = None
        # 循环查询次数，限制每个服务单元每次同步数据最大次数，防止循环卡死，或者服务单元接口问题造成无法跳出循环
        count = 6
        while count > 0:
            try:
                data = self.query_page_data(unit=unit, timestamp=timestamp)
            except Exception as exc:
                print(f'{dj_timezone.now()} error，{str(exc)}')
                return_err = exc
                break   # 错误结束循环

            if not data:
                break   # 数据同步完 结束循环

            ok, err, now_timestamp = self.write_data_to_db(data=data, unit_id=unit.id)
            if not ok:
                print(f'{dj_timezone.now()} error，{str(err)}')
                return_err = err
                break   # 错误结束循环

            if not now_timestamp:
                break

            timestamp = now_timestamp   # 从已同步时间戳继续同步
            count = count - 1

        return return_err

    def write_data_to_db(self, data: list, unit_id: int):
        """
        写入数据库
        :return:(
            bool    # True: success; False: has error
            err     # None or Exception
            timestamp: float    # 已经同步数据的时间戳；None时表示未同步任务数据
        )
        """
        obj_list = []
        err = None
        now_timestamp = None
        if not data:
            return True, err, now_timestamp

        for log_data in data:
            obj = self.build_log_model_obj(log_data=log_data, unit_id=unit_id)
            if not obj:
                continue

            obj_list.append(obj)
            if len(obj_list) == 200:
                try:
                    type(obj_list[0]).objects.bulk_create(objs=obj_list)
                except Exception as exc:
                    return False, exc, now_timestamp

                # 记录已经同步数据的时间戳，两端之中大的时间戳，防止查询数据排序倒序 造成一直查询重复数据
                now_timestamp = max(
                    self.get_timestamp_from_log_obj(obj_list[-1]), self.get_timestamp_from_log_obj(obj_list[0])
                )
                obj_list = []

        if obj_list:
            try:
                type(obj_list[0]).objects.bulk_create(objs=obj_list)
            except Exception as exc:
                return False, exc, now_timestamp

            # 记录已经同步数据的时间戳，两端之中大的时间戳，防止查询数据排序倒序 造成一直查询重复数据
            now_timestamp = max(
                self.get_timestamp_from_log_obj(obj_list[-1]), self.get_timestamp_from_log_obj(obj_list[0])
            )

        return True, None, now_timestamp

    @staticmethod
    def get_timestamp_from_log_obj(obj) -> float:
        return obj.creation_time.timestamp()


class ServerUnitSynchronizer(BaseSynchronizer):
    """
    云主机服务单元操作日志同步器
    """
    @staticmethod
    def get_service_units() -> List[ServerService]:
        qs = ServerService.objects.filter(status=ServerService.Status.ENABLE.value)
        return list(qs)

    @staticmethod
    def build_log_url(endpoint_url: str, timestamp: float) -> str:
        """
        数据按时间正序查询
        """
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query={'timestamp': timestamp})
        return f'{endpoint_url}/api/v3/logrecord/?{query}'

    def get_unit_start_timestamp(self, unit_id: int) -> Union[float, None]:
        """
        获取服务单元开始同步时间戳
        """
        log_data = ServerServiceLog.objects.filter(service_cell_id=unit_id).order_by('-creation_time').first()
        if log_data:
            return log_data.creation_time.timestamp()  # 时间戳

        return None

    @staticmethod
    def build_log_model_obj(log_data: dict, unit_id: int):
        try:
            creation_time = datetime.fromisoformat(log_data['create_time'])
            # creation_time = datetime.fromtimestamp(log_data['create_time'], tz=timezone.utc)
        except Exception as exc:
            print(f'日志创建时间无效，{log_data}')
            return None

        obj = ServerServiceLog(
            username=log_data['username'],
            content=log_data['operation_content'],
            creation_time=creation_time,
            service_cell_id=unit_id
        )
        obj.enforce_id()
        return obj

    def run(self):
        print(f'{dj_timezone.now()} Start sync server service unit log')
        try:
            units, err_units = self.do_sync_units_log()
        except Exception as exc:
            print(f'End with error: {str(exc)}')
        else:
            print(f'End，all units: {len(units)}, error units: {len(err_units)}')


class ObjectUnitSynchronizer(BaseSynchronizer):
    """
    对象存储服务单元操作日志同步器
    """
    @staticmethod
    def get_service_units() -> List[ObjectService]:
        qs = ObjectService.objects.filter(status=ServerService.Status.ENABLE.value)
        return list(qs)

    @staticmethod
    def build_log_url(endpoint_url: str, timestamp: float):
        """
        数据按时间正序查询
        """
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query={'timestamp': timestamp})
        return f'{endpoint_url}/api/v1/log/user/?{query}'

    def get_unit_start_timestamp(self, unit_id: int) -> Union[float, None]:
        """
        获取服务单元开始同步时间戳
        """
        log_data = ObjectServiceLog.objects.filter(service_cell_id=unit_id).order_by('-creation_time').first()
        if log_data:
            return log_data.creation_time.timestamp()  # 时间戳

        return None

    @staticmethod
    def build_log_model_obj(log_data: dict, unit_id: int):
        try:
            creation_time = datetime.fromisoformat(log_data['create_time'])
            # creation_time = datetime.fromtimestamp(log_data['create_time'], tz=timezone.utc)
        except Exception as exc:
            print(f'日志创建时间无效，{log_data}')
            return None

        obj = ObjectServiceLog(
            username=log_data['username'],
            content=log_data['operation_content'],
            creation_time=creation_time,
            service_cell_id=unit_id
        )
        obj.enforce_id()
        return obj

    def run(self):
        print(f'{dj_timezone.now()} Start sync object service unit log')
        try:
            units, err_units = self.do_sync_units_log()
        except Exception as exc:
            print(f'End with error: {str(exc)}')
        else:
            print(f'End，all units: {len(units)}, error units: {len(err_units)}')


class ServiceLogSynchronizer:
    """
    服务单元操作日志同步器
    """
    @staticmethod
    def run():
        ServerUnitSynchronizer().run()
        ObjectUnitSynchronizer().run()

