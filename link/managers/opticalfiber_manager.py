from django.utils.translation import gettext as _
from link.models import Element, OpticalFiber, FiberCable, ElementLink
from core import errors
from link.managers.element_manager import ElementManager
# from link.managers.fibercable_manager import FiberCableManager

class OpticalFiberManager:
    @staticmethod
    def get_queryset():
        return OpticalFiber.objects.all()

    @staticmethod
    def get_opticalfiber(id: str):
        """
        :raises: OpticalFiberNotExist
        """
        opticalfiber = OpticalFiberManager.get_queryset().filter(id=id).first()
        if opticalfiber is None:
            raise errors.TargetNotExist(message=_('光纤不存在'), code='OpticalFiberNotExist')
        return opticalfiber

    @staticmethod
    def create_opticalfiber(
        sequence: int,
        fibercable: FiberCable
    ) -> OpticalFiber:
        opticalfiber_id = OpticalFiber().generate_id()
        element = ElementManager.create_element(object_id=opticalfiber_id, object_type=Element.Type.OPTICAL_FIBER)
        opticalfiber = OpticalFiber(
            id=opticalfiber_id,
            fiber_cable=fibercable,
            sequence=sequence,
            element=element
        )
        opticalfiber.save(force_insert=True)

    @staticmethod
    def filter_queryset(is_linked: bool = None, fiber_cable_id: str = None):
        qs = OpticalFiberManager.get_queryset()
        if fiber_cable_id is not None:
            # tips:need verify fibercable existed?
            # fibercable = FiberCableManager.get_fibercable(fiber_cable_id)
            qs = qs.filter(fiber_cable_id=fiber_cable_id)
        if is_linked is not None:
            linked_element_id_list = ElementLink.get_linked_element_id_list()
            if is_linked is True:
                qs = qs.filter(element_id__in=linked_element_id_list)
            else:
                qs = qs.exclude(element_id__in=linked_element_id_list)
        return qs
