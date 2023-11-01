from django.utils.translation import gettext as _
from link.models import Element, OpticalFiber, FiberCable
from core import errors
from link.managers.element_manager import ElementManager

class OpticalFiberManager:
    @staticmethod
    def get_queryset():
        return OpticalFiber.objects.all()

    @staticmethod
    def get_opticalfiber(id: str):
        """
        :raises: OpticalFiberNotExist
        """
        opticalfiber = OpticalFiber.objects.filter(id=id).first()
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
