from django.utils.translation import gettext as _
from link.models import ElementLink, Element, LeaseLine, Task
from core import errors
from django.db.models import Case, When
from link.managers.element_manager import ElementManager


class ElementLinkManager:
    @staticmethod
    def get_queryset():
        return ElementLink.objects.all()

    @staticmethod
    def get_elementlink(id: str):
        """
        :raises: LeaseLineNotExist
        """
        elementlink = ElementLink.objects.filter(id=id).first()
        if elementlink is None:
            raise errors.TargetNotExist(message=_('租用线路不存在'), code='ElementLinkNotExist')
        return elementlink

    @staticmethod
    def get_element_ids_by_element_list(element_list: list) -> str:
        """通过网元列表获得网元id序列字符串"""
        return ','.join([element.id for element in element_list])

    @staticmethod
    def get_element_list_by_element_ids(element_ids: str) -> list:
        """通过网元id序列字符串获得网元列表"""
        element_id_list = element_ids.split(',')
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(element_id_list)])
        return list(Element.objects.filter(id__in=element_id_list).order_by(preserved))

    @staticmethod
    def create_elementlink(
            number: str,
            elements: list,
            remarks: str,
            link_status: ElementLink.LinkStatus,
            task: Task
    ) -> LeaseLine:
        if number is None:
            # todo generate number
            pass
        if elements is None or len(elements) == 0:
            # elements empty error
            raise errors.Error(message=_('ElementLinkManager create_elementlink elements_empty'))

        elements = [ElementManager.get_element_by_object(
            object_type=element['object_type'],
            object_id=element['object_id']
        )
            for element in elements]

        elementlink = ElementLink(
            number=number,
            element_ids=ElementLinkManager.get_element_ids_by_element_list(elements),
            remarks=remarks,
            task=task,
            link_status=link_status
        )
        elementlink.save()
        return elementlink
