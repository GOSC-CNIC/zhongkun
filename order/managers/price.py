from decimal import Decimal

from django.utils import timezone

from utils.time import datetime_add_months
from core import errors
from order.models import Price


class PriceManager:
    @staticmethod
    def get_price():
        """
        :return: Price() or None
        """
        return Price.objects.order_by('-creation_time').first()

    def enforce_price(self) -> Price:
        """
        :raises: NoPrice
        """
        price = self.get_price()
        if price is None:
            raise errors.NoPrice()

        return price

    @staticmethod
    def period_month_days(months: int):
        """
        每月按30天计算
        """
        return 30 * months

    def describe_disk_price(self, size_gib: int, is_prepaid: bool, period: int = None) -> (Decimal, Decimal):
        """
        云硬盘询价

        :param size_gib: disk size GiB
        :param is_prepaid: True(包年包月预付费)，False(按量计费)
        :param period: 时长，单位月数，默认None(一天)
        :return:
            (
                original_price,    # 原价
                trade_price        # 减去折扣的价格
            )
        :raises: NoPrice
        """
        price = self.enforce_price()
        day_price = price.disk_size * size_gib
        if period is None:
            original_price = day_price
        else:
            days = self.period_month_days(period)
            original_price = day_price * days

        if is_prepaid:
            trade_price = original_price * Decimal.from_float(price.prepaid_discount / 100)
        else:
            trade_price = original_price

        return original_price, trade_price

    def describe_server_price(
            self,
            ram_mib: int,
            cpu: int,
            disk_gib: int,
            public_ip: bool,
            is_prepaid: bool,
            period: int = None
    ) -> (Decimal, Decimal):
        """
        云主机询价

        :param size_gib: disk size GiB
        :param is_prepaid: True(包年包月预付费)，False(按量计费)
        :param period: 时长，单位月数，默认None(一天)
        :return:
            (
                original_price,    # 原价
                trade_price        # 减去折扣的价格
            )
        :raises: NoPrice
        """
        price = self.enforce_price()
        p_ram = price.vm_ram * Decimal.from_float(ram_mib / 1024)
        p_cpu = price.vm_cpu * Decimal.from_float(cpu)
        p_disk = price.vm_disk * Decimal.from_float(disk_gib)
        day_price = p_ram + p_disk + p_cpu
        if public_ip:
            day_price += price.vm_pub_ip

        if period is None:
            original_price = day_price
        else:
            days = self.period_month_days(period)
            original_price = day_price * days

        if is_prepaid:
            trade_price = original_price * Decimal.from_float(price.prepaid_discount / 100)
        else:
            trade_price = original_price

        return original_price, trade_price

    def describe_bucket_price(self) -> (Decimal, Decimal):
        """
        对象存储询价

        :return:
            (
                original_price,    # 原价, GiB/day price
                trade_price        # 减去折扣的价格, GiB/day price
            )
        :raises: NoPrice
        """
        price = self.enforce_price()
        return price.obj_size, price.obj_size
