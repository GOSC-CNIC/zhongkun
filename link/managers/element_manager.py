from django.utils.translation import gettext as _
from link.models import Element, ElementLink
from core import errors
from link.utils.verify_utils import VerifyUtils
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

    @staticmethod
    def is_linked(element_id:str) -> bool:
        if VerifyUtils.is_blank_string(element_id):
            raise errors.Error(message=_('ElementManager is_linked element_id_blank'))
        return ElementLink.objects.exclude(link_status = ElementLink.LinkStatus.DELETED).filter(element_ids__icontains=element_id).exists()