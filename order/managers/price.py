from decimal import Decimal

from core import errors
from order.models import Price


class PriceManager:
    def __init__(self):
        self._price = None

    @staticmethod
    def get_price():
        """
        :return: Price() or None
        """
        return Price.objects.order_by('-creation_time').first()

    def enforce_price(self, refresh: bool = False) -> Price:
        """
        :raises: NoPrice
        """
        if self._price is None or refresh:
            self._price = self.get_price()
            if self._price is None:
                raise errors.NoPrice()

        return self._price

    @staticmethod
    def period_month_days(months: int):
        """
        每月按30天计算
        """
        return 30 * months

    def describe_disk_price(
            self, size_gib: int, is_prepaid: bool, period: int, days: float
    ) -> (Decimal, Decimal):
        """
        云硬盘询价
        总时长 = period + days
        :param size_gib: disk size GiB
        :param is_prepaid: True(包年包月预付费)，False(按量计费)
        :param period: 时长，单位月数
        :param days: 时长天数，默认一天
        :return:
            (
                original_price,    # 原价
                trade_price        # 减去折扣的价格
            )
        :raises: NoPrice
        """
        total_days = days
        if period and period > 0:
            period_days = self.period_month_days(period)
            total_days += period_days

        price = self.enforce_price()
        hour_price = price.disk_size * size_gib
        original_price = hour_price * Decimal.from_float(total_days * 24)
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
            period: int,
            days: float
    ) -> (Decimal, Decimal):
        """
        云主机询价
        总时长 = period + days
        :param ram_mib:
        :param cpu:
        :param disk_gib: disk size GiB
        :param public_ip:
        :param is_prepaid: True(包年包月预付费)，False(按量计费)
        :param period: 时长，单位月数
        :param days: 时长天数，默认一天
        :return:
            (
                original_price,    # 原价
                trade_price        # 减去折扣的价格
            )
        :raises: NoPrice
        """
        total_days = days
        if period and period > 0:
            period_days = self.period_month_days(period)
            total_days += period_days

        price = self.enforce_price()
        total_hours = 24 * total_days
        ram_gib_hours = ram_mib / 1024 * total_hours
        cpu_hours = cpu * total_hours
        disk_gib_hours = disk_gib * total_hours
        if public_ip:
            public_ip_hours = total_hours
        else:
            public_ip_hours = 0

        original_price = self.calculate_server_amount(
            price=price,
            ram_gib_hours=ram_gib_hours,
            cpu_hours=cpu_hours,
            disk_gib_hours=disk_gib_hours,
            public_ip_hours=public_ip_hours
        )

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
        day_price = price.obj_size * Decimal('24')
        return day_price, day_price

    def describe_server_metering_price(
            self,
            ram_gib_hours: float,
            cpu_hours: float,
            disk_gib_hours: float,
            public_ip_hours: float
    ) -> Decimal:
        """
        按量计费云主机计价
        """
        price = self.enforce_price()
        return self.calculate_server_amount(
            price=price,
            ram_gib_hours=ram_gib_hours,
            cpu_hours=cpu_hours,
            disk_gib_hours=disk_gib_hours,
            public_ip_hours=public_ip_hours
        )

    @staticmethod
    def calculate_server_amount(
            price: Price,
            ram_gib_hours: float,
            cpu_hours: float,
            disk_gib_hours: float,
            public_ip_hours: float
    ) -> Decimal:
        """
        计算金额
        """
        ram_amount = price.vm_ram * Decimal.from_float(ram_gib_hours)
        cpu_amount = price.vm_cpu * Decimal.from_float(cpu_hours)
        disk_amount = price.vm_disk * Decimal.from_float(disk_gib_hours)
        ip_amount = price.vm_pub_ip * Decimal.from_float(public_ip_hours)
        return ram_amount + cpu_amount + disk_amount + ip_amount

    @staticmethod
    def calculate_bucket_amounts(
            price: Price,
            storage_gib_hours: float,
            hours: float
    ) -> Decimal:
        """
        计算金额
        """
        amounts = price.obj_size / Decimal('24') * Decimal.from_float(storage_gib_hours)
        amounts += Decimal('0.06') / Decimal('24') * Decimal.from_float(hours)   # +桶每天的基础费用
        return amounts
