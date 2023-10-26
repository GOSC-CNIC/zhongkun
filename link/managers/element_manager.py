from django.utils.translation import gettext as _
from link.models import Element
from core import errors

class ElementManager:
    @staticmethod
    def get_queryset():
        return Element.objects.all()

    @staticmethod
    def get_element_by_id(
            id: str,
    ) -> Element:
        element = Element.objects.filter(id=id).first()
        if element is None:
            raise errors.TargetNotExist(message=_('网元不存在'), code='ElementNotExist')
        return element
    
    @staticmethod
    def get_element_by_object(
            object_type: str,
            object_id: str,
    ) -> Element:
        element = Element.objects.filter(object_id=object_id, object_type=object_type).first()
        if element is None:
            raise errors.TargetNotExist(message=_('网元不存在'), code='ElementNotExist')
        return element
    
    @staticmethod
    def create_element(
            object_id: str,
            object_type: Element.Type
    ) -> Element:
        element = Element(
            object_id=object_id,
            object_type=object_type,
        )
        element.save(force_insert=True)
        return element
    
