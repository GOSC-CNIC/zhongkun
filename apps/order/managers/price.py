from decimal import Decimal

from core import errors
from apps.order.models import Price, Order


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
    def convert_period_days(period: int, period_unit: str):
        """
        每月按30天计算
        """
        if period_unit == Order.PeriodUnit.DAY.value:
            return period
        elif period_unit == Order.PeriodUnit.MONTH.value:
            return 30 * period
        else:
            raise Exception('无效的时长单位')

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
            period_days = self.convert_period_days(period=period, period_unit=Order.PeriodUnit.MONTH.value)
            total_days += period_days

        price = self.enforce_price()
        size_gib_days = size_gib * total_days
        original_price = self.calculate_disk_amounts(price=price, size_gib_days=size_gib_days)
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
            period_unit: str,
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
        :param period: 时长
        :param period_unit: 时长单位
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
            period_days = self.convert_period_days(period=period, period_unit=period_unit)
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

    @staticmethod
    def calculate_disk_amounts(
            price: Price,
            size_gib_days: float
    ) -> Decimal:
        """
        计算金额
        """
        # 价格是按天
        amounts = price.disk_size * Decimal.from_float(size_gib_days)
        return amounts

    @staticmethod
    def calculate_monitor_site_amounts(
            price: Price, days: float,
            detection_count: int, tamper_count: int, security_count: int
    ) -> Decimal:
        """
        计算金额
        """
        # 价格是按天
        days_amount = price.mntr_site_base
        if tamper_count > 0:
            days_amount += price.mntr_site_tamper
        if security_count > 0:
            days_amount += price.mntr_site_security

        return days_amount * Decimal.from_float(days)

    def describe_scan_price(self, has_host: bool, has_web: bool) -> (Decimal, Decimal):
        """
        安全扫描询价

        :param has_host: True(host扫描)
        :param has_web: True(web扫描)
        :return:
            (
                original_price,    # 原价
                trade_price        # 减去折扣的价格
            )
        :raises: NoPrice
        """
        price = self.enforce_price()
        original_price = Decimal('0')
        if has_web:
            original_price += price.scan_web

        if has_host:
            original_price += price.scan_host

        trade_price = original_price * Decimal.from_float(price.prepaid_discount / 100)
        return original_price, trade_price
