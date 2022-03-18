from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from servers.models import Flavor

from api.viewsets import CustomGenericViewSet
from order.models import ResourceType
from order.managers import PriceManager
from utils.decimal_utils import quantize_12_4


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
            flavor = Flavor.objects.filter(id=flavor_id, enable=True).first()
            if not flavor:
                return view.exception_response(errors.BadRequest(message=_('无效的flavor id')))

            original_price, trade_price = pmgr.describe_server_price(
                ram_mib=flavor.ram, cpu=flavor.vcpus, disk_gib=system_disk_size, public_ip=external_ip,
                is_prepaid=(pay_type == 'prepaid'), period=period)
        elif resource_type == ResourceType.DISK:
            pay_type = data['pay_type']
            data_disk_size = data['data_disk_size']
            period = data['period']
            original_price, trade_price = pmgr.describe_disk_price(
                size_gib=data_disk_size, is_prepaid=(pay_type == 'prepaid'), period=period)
        else:
            original_price, trade_price = pmgr.describe_bucket_price()

        return Response(data={
            'price': {
                'original': str(quantize_12_4(original_price)),
                'trade': str(quantize_12_4(trade_price))
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
        else:
            return ResourceType.BUCKET, {}

    @staticmethod
    def param_period_validate(request):
        """
        :return: int or None
        """
        period = request.query_params.get('period', None)
        if period is not None:
            try:
                period = int(period)
            except ValueError:
                raise errors.InvalidArgument(message=_('参数“period”的值无效'))

            if period <= 0:
                raise errors.InvalidArgument(message=_('参数“period”的值无效，必须大于0'))

        return period

    def validate_vm_params(self, request):
        params = request.query_params
        flavor_id = params.get('flavor_id', None)
        external_ip = params.get('external_ip', None)
        system_disk_size = params.get('system_disk_size', None)
        pay_type = params.get('pay_type', None)
        period = self.param_period_validate(request)

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
            'period': period
        }

    def validate_disk_params(self, request):
        params = request.query_params
        data_disk_size = params.get('data_disk_size', None)
        pay_type = params.get('pay_type', None)
        period = self.param_period_validate(request)

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
            'period': period
        }
