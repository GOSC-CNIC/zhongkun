from django.utils.translation import gettext as _
from link.models import FiberCable, Element, OpticalFiber
from django.db.models import Q
from core import errors
from link.managers.element_manager import ElementManager
from django.db import transaction

class FiberCableManager:
    @staticmethod
    def get_queryset():
        return FiberCable.objects.all()

    @staticmethod
    def get_fibercable(id: str):
        """
        :raises: FiberCableNotExist
        """
        fibercable = FiberCable.objects.filter(id=id).first()
        if fibercable is None:
            raise errors.TargetNotExist(message=_('光缆不存在'), code='FiberCableNotExist')
        return fibercable
        
    def _create_opticalfiber(
        sequence: int,
        fibercable: FiberCable
    ) -> OpticalFiber:
        fibercable_id = OpticalFiber().generate_id()
        element = ElementManager.create_element(object_id=fibercable_id, object_type=Element.Type.OPTICAL_FIBER)
        opticalfiber = OpticalFiber(
            fiber_cable=fibercable,
            sequence=sequence,
            element=element
        )
        opticalfiber.save(force_insert=True)
        
    @staticmethod
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
                number = number,
                fiber_count = fiber_count,
                length = length,
                endpoint_1 = endpoint_1,
                endpoint_2 = endpoint_2,
                remarks=remarks
            )
            fibercable.save(force_insert=True)
            # 创建光纤记录
            for i in range(1, fiber_count + 1):
                FiberCableManager._create_opticalfiber(sequence=i, fibercable=fibercable)

        return fibercable
    
    @staticmethod
    def filter_queryset(search: str = None):
        qs = FiberCableManager.get_queryset()
        lookups = {}
        qs = qs.filter(**lookups)
        if search:
            q = Q(number__icontains=search) | Q(endpoint_1__icontains=search) | Q(endpoint_2__icontains=search) | Q(remarks__icontains=search)
            qs = qs.filter(q)
        return qs
