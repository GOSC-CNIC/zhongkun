from datetime import datetime

from django.utils.translation import gettext as _
from django.utils import timezone
from django.db import models
from rest_framework.response import Response

from core import errors
from servers.models import Flavor

from api.viewsets import CustomGenericViewSet
from order.models import ResourceType
from order.managers import PriceManager
from utils.decimal_utils import quantize_10_2
from utils.time import iso_utc_to_datetime
from servers.managers import ServerManager, DiskManager


class ScanTaskType(models.TextChoices):
    HOST = 'host', 'Host'
    WEB = 'web', 'Web'


class DescribePriceHandler:
    def describe_price(self, view: CustomGenericViewSet, request):
        try:
            resource_type, data = self.validate_params(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        pmgr = PriceManager()
        if resource_type == ResourceType.VM:
            pay_type = data['pay_type']
            flavor_id = data['flavor_id']
            external_ip = data['external_ip']
            system_disk_size = data['system_disk_size']
            period = data['period']
            days = 1 if period is None else 0

            flavor = Flavor.objects.filter(id=flavor_id, enable=True).first()
            if not flavor:
                return view.exception_response(errors.BadRequest(message=_('无效的flavor id')))

            original_price, trade_price = pmgr.describe_server_price(
                ram_mib=flavor.ram_mib, cpu=flavor.vcpus, disk_gib=system_disk_size, public_ip=external_ip,
                is_prepaid=(pay_type == 'prepaid'), period=period, days=days)

            number = data['number']
            if number > 1:
                original_price = original_price * number
                trade_price = trade_price * number
        elif resource_type == ResourceType.DISK:
            pay_type = data['pay_type']
            data_disk_size = data['data_disk_size']
            period = data['period']
            days = 1 if period is None else 0

            original_price, trade_price = pmgr.describe_disk_price(
                size_gib=data_disk_size, is_prepaid=(pay_type == 'prepaid'), period=period, days=days)

            number = data['number']
            if number > 1:
                original_price = original_price * number
                trade_price = trade_price * number
        elif resource_type == ResourceType.BUCKET.value:
            original_price, trade_price = pmgr.describe_bucket_price()
        elif resource_type == ResourceType.SCAN.value:
            scan_tasks = data['scan_task']
            original_price, trade_price = pmgr.describe_scan_price(
                has_host=ScanTaskType.HOST.value in scan_tasks,
                has_web=ScanTaskType.WEB.value in scan_tasks
            )
        else:
            return view.exception_response(errors.BadRequest(message=_('资源类型不支持询价')))

        return Response(data={
            'price': {
                'original': str(quantize_10_2(original_price)),
                'trade': str(quantize_10_2(trade_price))
            }
        })

    def validate_params(self, request):
        resource_type = request.query_params.get('resource_type', None)

        if resource_type is None:
            raise errors.NoFoundArgument(message=_('必须指定参数“resource_type”'))

        if resource_type not in ResourceType.values:
            raise errors.InvalidArgument(message=_('参数“resource_type”的值无效'))

        if resource_type == ResourceType.VM:
            data = self.validate_vm_params(request)
            return ResourceType.VM, data
        elif resource_type == ResourceType.DISK:
            data = self.validate_disk_params(request)
            return ResourceType.DISK, data
        elif resource_type == ResourceType.SCAN.value:
            data = self.validate_scan_params(request)
            return ResourceType.SCAN.value, data
        else:
            return ResourceType.BUCKET, {}

    @staticmethod
    def param_period_validate(period):
        """
        :return: int or None
        """
        if period is not None:
            try:
                period = int(period)
            except ValueError:
                raise errors.InvalidArgument(message=_('参数“period”的值无效'))

            if period <= 0:
                raise errors.InvalidArgument(message=_('参数“period”的值无效，必须大于0'))

        return period

    @staticmethod
    def param_number_validate(number: str):
        """
        :return: int
        """
        if number is None:
            return 1

        try:
            number = int(number)
        except ValueError:
            raise errors.InvalidArgument(message=_('订购资源数量无效'))

        if not (1 <= number <= 3):
            raise errors.InvalidArgument(message=_('订购资源数量只允许1-3'))

        return number

    def validate_vm_params(self, request):
        params = request.query_params
        flavor_id = params.get('flavor_id', None)
        external_ip = params.get('external_ip', None)
        system_disk_size = params.get('system_disk_size', None)
        pay_type = params.get('pay_type', None)
        period = request.query_params.get('period', None)
        number = request.query_params.get('number', None)

        period = self.param_period_validate(period=period)
        number = self.param_number_validate(number=number)

        if pay_type not in ['prepaid', 'postpaid']:
            raise errors.InvalidArgument(message=_('参数“pay_type”的值无效'))

        if flavor_id is None:
            raise errors.NoFoundArgument(message=_('参数resource_type=vm时，必须指定参数“flavor_id”'))

        if external_ip is not None:
            external_ip = external_ip.lower()
            if external_ip == 'true':
                external_ip = True
            elif external_ip == 'false':
                external_ip = False
            else:
                raise errors.InvalidArgument(message=_('参数“external_ip”的值无效'))
        else:
            external_ip = False

        if system_disk_size is None:
            system_disk_size = 0
        else:
            try:
                system_disk_size = int(system_disk_size)
            except ValueError:
                raise errors.InvalidArgument(message=_('参数“system_disk_size”的值无效'))

            if system_disk_size < 0:
                raise errors.InvalidArgument(message=_('参数“system_disk_size”的值无效, 不能小于零'))

        return {
            'pay_type': pay_type,
            'flavor_id': flavor_id,
            'external_ip': external_ip,
            'system_disk_size': system_disk_size,
            'period': period,
            'number': number
        }

    def validate_disk_params(self, request):
        params = request.query_params
        data_disk_size = params.get('data_disk_size', None)
        pay_type = params.get('pay_type', None)
        period = request.query_params.get('period', None)
        number = request.query_params.get('number', None)

        period = self.param_period_validate(period=period)
        number = self.param_number_validate(number=number)

        if pay_type not in ['prepaid', 'postpaid']:
            raise errors.InvalidArgument(message=_('参数“pay_type”的值无效'))

        if data_disk_size is None:
            raise errors.NoFoundArgument(message=_('必须指定参数“data_disk_size”'))

        try:
            data_disk_size = int(data_disk_size)
        except ValueError:
            raise errors.InvalidArgument(message=_('参数“data_disk_size”的值无效'))

        if data_disk_size < 0:
            raise errors.InvalidArgument(message=_('参数“data_disk_size”的值无效, 不能小于零'))

        return {
            'pay_type': pay_type,
            'data_disk_size': data_disk_size,
            'period': period,
            'number': number
        }

    @staticmethod
    def validate_scan_params(request):
        scan_task = request.query_params.getlist('scan_task', [])
        if not scan_task:
            raise errors.InvalidArgument(message=_('请指定要询价的安全扫描任务类型'))

        tasks = set(scan_task)
        if len(tasks) != len(scan_task):
            raise errors.InvalidArgument(message=_('指定的安全扫描任务类型重复'))

        for tt in tasks:
            if tt not in ScanTaskType.values:
                raise errors.InvalidArgument(message=_('指定的安全扫描任务类型无效'))

        return {
            'scan_task': tasks
        }

    def _describe_renewal_price_validate_params(self, request):
        resource_type = request.query_params.get('resource_type', None)
        instance_id = request.query_params.get('instance_id', None)
        period = request.query_params.get('period', None)
        renew_to_time = request.query_params.get('renew_to_time', None)

        if resource_type is None:
            raise errors.InvalidArgument(message=_('参数“resource_type”未设置'), code='MissingResourceType')

        if resource_type not in [ResourceType.VM.value, ResourceType.DISK.value]:
            raise errors.InvalidArgument(message=_('无效的资源类型'), code='InvalidResourceType')

        if instance_id is None:
            raise errors.InvalidArgument(message=_('参数“instance_id”未设置'), code='MissingInstanceId')

        if not instance_id:
            raise errors.InvalidArgument(message=_('参数“instance_id”的值无效'), code='InvalidInstanceId')

        if period is not None and renew_to_time is not None:
            raise errors.BadRequest(
                message=_('参数“period”和“renew_to_time”不能同时提交'), code='PeriodConflictRenewToTime')

        if period is None and renew_to_time is None:
            raise errors.BadRequest(message=_('参数“period”不得为空'), code='MissingPeriod')

        if period is not None:
            try:
                period = self.param_period_validate(period=period)
            except errors.Error as exc:
                raise errors.InvalidArgument(message=exc.message, code='InvalidPeriod')
        else:
            renew_to_time = iso_utc_to_datetime(renew_to_time)
            if not isinstance(renew_to_time, datetime):
                raise errors.InvalidArgument(
                    message=_('参数“renew_to_time”的值无效的时间格式'), code='InvalidRenewToTime')

        return {
            'resource_type': resource_type,
            'instance_id': instance_id,
            'period': period,
            'renew_to_time': renew_to_time
        }

    def describe_renewal_price(self, view: CustomGenericViewSet, request):
        try:
            params = self._describe_renewal_price_validate_params(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        resource_type = params['resource_type']
        instance_id = params['instance_id']
        period = params['period']
        renew_to_time = params['renew_to_time']

        pmgr = PriceManager()
        if resource_type == ResourceType.VM.value:
            try:
                server = ServerManager().get_server(server_id=instance_id)
            except errors.NotFound:
                return view.exception_response(exc=errors.NotFound(message=_('资源实例不存在'), code='NotFoundInstanceId'))

            days = 0
            if renew_to_time:
                expiration_time = server.expiration_time if server.expiration_time else timezone.now()
                if renew_to_time <= expiration_time:
                    return view.exception_response(errors.ConflictError(
                        message=_('参数“renew_to_time”指定的日期不能在资源实例的过期时间之前'), code='InvalidRenewToTime'))

                delta = renew_to_time - expiration_time
                days = delta.days + delta.seconds / (3600 * 24)

            original_price, trade_price = pmgr.describe_server_price(
                ram_mib=server.ram_mib, cpu=server.vcpus, disk_gib=server.disk_size, public_ip=server.public_ip,
                is_prepaid=(server.pay_type == 'prepaid'), period=period, days=days)
        elif resource_type == ResourceType.DISK.value:
            try:
                disk = DiskManager().get_disk(disk_id=instance_id)
            except errors.NotFound:
                return view.exception_response(exc=errors.NotFound(message=_('资源实例不存在'), code='NotFoundInstanceId'))
            days = 0
            if renew_to_time:
                expiration_time = disk.expiration_time if disk.expiration_time else timezone.now()
                if renew_to_time <= expiration_time:
                    return view.exception_response(errors.ConflictError(
                        message=_('参数“renew_to_time”指定的日期不能在资源实例的过期时间之前'), code='InvalidRenewToTime'))

                delta = renew_to_time - expiration_time
                days = delta.days + delta.seconds / (3600 * 24)

            original_price, trade_price = pmgr.describe_disk_price(
                size_gib=disk.size,
                is_prepaid=(disk.pay_type == 'prepaid'), period=period, days=days)
        else:
            return view.exception_response(
                exc=errors.InvalidArgument(message=_('无效的资源类型'), code='InvalidResourceType'))

        return Response(data={
            'price': {
                'original': str(quantize_10_2(original_price)),
                'trade': str(quantize_10_2(trade_price))
            }
        })
