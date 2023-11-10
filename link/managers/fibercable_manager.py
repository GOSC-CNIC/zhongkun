from django.utils.translation import gettext as _
from link.models import FiberCable
from django.db.models import Q
from core import errors
from link.managers.opticalfiber_manager import OpticalFiberManager
from django.db import transaction


class FiberCableManager:
    def get_queryset():
        return FiberCable.objects.all()

    def get_fibercable(id: str):
        """
        :raises: FiberCableNotExist
        """
        fibercable = FiberCableManager.get_queryset().filter(id=id).first()
        if fibercable is None:
            raise errors.TargetNotExist(message=_('光缆不存在'), code='FiberCableNotExist')
        return fibercable

    def create_fibercable(
            number: str,
            fiber_count: int,
            length: float,
            endpoint_1: str,
            endpoint_2: str,
            remarks: str
    ) -> FiberCable:
        with transaction.atomic():
            # 创建光缆记录
            fibercable = FiberCable(
                number=number,
                fiber_count=fiber_count,
                length=length,
                endpoint_1=endpoint_1,
                endpoint_2=endpoint_2,
                remarks=remarks
            )
            fibercable.save(force_insert=True)
            # 创建光纤记录
            for i in range(1, fiber_count + 1):
                OpticalFiberManager.create_opticalfiber(sequence=i, fibercable=fibercable)

        return fibercable

    def filter_queryset(search: str = None):
        qs = FiberCableManager.get_queryset()
        if qs is not None and search is not None:
            q = Q(number__icontains=search) | Q(endpoint_1__icontains=search) \
                | Q(endpoint_2__icontains=search) | Q(remarks__icontains=search)
            qs = qs.filter(q)
        return qs

    def get_opticalfiber_queryset(fibercable: FiberCable):
        if fibercable is not None:
            return fibercable.fibercable_opticalfiber.all()
