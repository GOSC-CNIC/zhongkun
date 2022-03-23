from decimal import Decimal

from django.utils.translation import gettext as _
from django.db import transaction

from utils.model import OwnerType, PayType
from servers.models import get_uuid1_str
from core import errors
from order.models import Order, Resource, ResourceType
from .instance_configs import BaseConfig, ServerConfig, DiskConfig, BucketConfig
from .price import PriceManager


class OrderManager:
    def create_order(
            self, order_type,
            service_id,
            service_name,
            resource_type,
            instance_config,
            period,
            pay_type,
            user_id,
            username,
            vo_id,
            vo_name,
            owner_type
    ) -> (Order, Resource):
        """
        提交一个订单

        :param instance_config: BaseConfig
        :return:
            order, resource

        :raises: Error
        """
        if owner_type not in OwnerType.values:
            raise errors.Error(message=_('无法创建订单，订单所属类型无效'))

        if resource_type not in ResourceType.values:
            raise errors.Error(message=_('无法创建订单，资源类型无效'))

        if pay_type not in PayType.values:
            raise errors.Error(message=_('无法创建订单，资源计费方式pay_type无效'))
        if pay_type == PayType.PREPAID.value:         # 预付费
            total_amount, pay_amount = self.calculate_amount_money(
                resource_type=resource_type, config=instance_config, is_prepaid=True, period=period)
        else:
            total_amount = pay_amount = Decimal(0)

        order = Order(
            order_type=order_type,
            status=Order.Status.UPPAID.value,
            total_amount=total_amount,
            pay_amount=pay_amount,
            service_id=service_id,
            service_name=service_name,
            resource_type=resource_type,
            instance_config=instance_config.to_dict(),
            period=period,
            pay_type=pay_type,
            payment_time=None,
            user_id=user_id,
            username=username,
            vo_id=vo_id,
            vo_name=vo_name,
            owner_type=owner_type
        )

        instance_id = get_uuid1_str()
        with transaction.atomic():
            order.save(force_insert=True)
            resource = Resource(
                id=instance_id, order=order, resource_type=resource_type, instance_id=instance_id
            )
            resource.save(force_insert=True)

        return order, resource

    @staticmethod
    def calculate_amount_money(
            resource_type, config: BaseConfig, is_prepaid, period: int = None
    ) -> (Decimal, Decimal):
        """
        计算资源金额

        :param is_prepaid: True(预付费)， False(按量计费)
        :param period: 预付费时长（月），默认None(时长一天)
        """
        if resource_type == ResourceType.VM.value:
            if not isinstance(config, ServerConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price, trade_price = PriceManager().describe_server_price(
                ram_mib=config.vm_ram, cpu=config.vm_cpu, disk_gib=config.vm_systemdisk_size,
                public_ip=config.vm_public_ip, is_prepaid=is_prepaid, period=period
            )
        elif resource_type == ResourceType.DISK.value:
            if not isinstance(config, DiskConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price, trade_price = PriceManager().describe_disk_price(
                size_gib=config.disk_size, is_prepaid=is_prepaid, period=period
            )
        elif resource_type == ResourceType.BUCKET.value:
            if not isinstance(config, BucketConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price = trade_price = Decimal(0)
        else:
            raise errors.Error(message=_('无法计算资源金额，资源类型无效'))

        return original_price, trade_price

    @staticmethod
    def get_order_queryset():
        return Order.objects.all()

    def filter_order_queryset(
            self, resource_type: str, order_type: str, status: str, time_start, time_end, user_id: str, vo_id: str
    ):
        """
        查询用户或vo组的订单查询集
        """
        queryset = self.get_order_queryset()
        if user_id:
            queryset = queryset.filter(user_id=user_id, owner_type=OwnerType.USER.value)

        if vo_id:
            queryset = queryset.filter(vo_id=vo_id, owner_type=OwnerType.VO.value)

        if time_start:
            queryset = queryset.filter(creation_time__gte=time_start)

        if time_end:
            queryset = queryset.filter(creation_time__lte=time_end)

        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        if order_type:
            queryset = queryset.filter(order_type=order_type)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-creation_time')
