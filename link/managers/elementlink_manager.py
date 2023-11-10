from django.utils.translation import gettext as _
from link.models import ElementLink, Element, LeaseLine, Task
from core import errors
from django.db.models import Case, When

class ElementLinkManager:
    def get_queryset():
        return ElementLink.objects.exclude(link_status=ElementLink.LinkStatus.DELETED)

    def get_elementlink(id: str):
        """
        :raises: LeaseLineNotExist
        """
        elementlink = ElementLinkManager.get_queryset().filter(id=id).first()
        if elementlink is None:
            raise errors.TargetNotExist(message=_('租用线路不存在'), code='ElementLinkNotExist')
        return elementlink

    def get_element_ids_by_element_list(element_list: list) -> str:
        """通过网元列表获得网元id序列字符串"""
        return ','.join([element.id for element in element_list])

    def get_element_list_by_element_ids(element_ids: str) -> list:
        """通过网元id序列字符串获得网元列表"""
        element_id_list = element_ids.split(',')
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(element_id_list)])
        return list(Element.objects.filter(id__in=element_id_list).order_by(preserved))

    def _generate_default_number():
        # todo generate number
        pass

    def create_elementlink(
            id_list: list,
            remarks: str,
            link_status: ElementLink.LinkStatus,
            task: Task = None,
            number: str = None,
    ) -> LeaseLine:
        # if VerifyUtils.is_blank_string(number):
        #     number = ElementLinkManager._generate_default_number()
        # if VerifyUtils.is_empty_list(id_list):
        #     # elements empty error
        #     raise errors.Error(message=_('ElementLinkManager create_elementlink id_list_empty'))
        if number is None:
            number = ElementLinkManager._generate_default_number()
        elementlink = ElementLink(
            number=number,
            element_ids=ElementLink.get_element_ids_by_id_list(id_list),
            remarks=remarks,
            task=task,
            link_status=link_status
        )
        elementlink.save()
        return elementlink

    def filter_queryset(task_id: str = None):
        qs = ElementLinkManager.get_queryset()
        if task_id is not None:
            qs = qs.filter(task_id=task_id)

        return qs
