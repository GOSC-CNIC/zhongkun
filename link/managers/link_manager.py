from django.utils.translation import gettext as _
from link.models import Link, Element, ElementLink
from core import errors
from django.db import transaction
from datetime import date
from link.managers.element_manager import ElementManager

class LinkManager:
    @staticmethod
    def get_queryset():
        return Link.objects.all()

    @staticmethod
    def get_link(id: str):
        """
        :raises: LinkNotExist
        """
        link = LinkManager.get_queryset().filter(id=id).first()
        if link is None:
            raise errors.TargetNotExist(message=_('链路不存在'), code='LinkNotExist')
        return link

    @staticmethod
    def create_elementlink(
        element: Element,
        link: Link,
        index: int,
        sub_index: int = 0,
    ) -> ElementLink:
        elementlink = ElementLink(
            element=element,
            link=link,
            index=index,
            sub_index=sub_index
        )
        elementlink.save(force_insert=True)
        return elementlink

    @staticmethod
    def create_link(
            number: str,
            user: str,
            endpoint_a: str,
            endpoint_z: str,
            bandwidth: float,
            description: str,
            line_type: str,
            business_person: str,
            build_person: str,
            link_status: str,
            remarks: str,
            enable_date: date,
            link_element: list,
    ) -> Link:
        with transaction.atomic():
            link = Link(
                number=number,
                user=user,
                endpoint_a=endpoint_a,
                endpoint_z=endpoint_z,
                bandwidth=bandwidth,
                description=description,
                line_type=line_type,
                business_person=business_person,
                build_person=build_person,
                link_status=link_status,
                remarks=remarks,
                enable_date=enable_date,
            )
            link.save(force_insert=True)
            for t in link_element:
                element = ElementManager.get_element_by_id(t['element_id'])
                LinkManager.create_elementlink(
                    element=element, link=link, 
                    index=t['index'], sub_index=t['sub_index'])
        return link

    @staticmethod
    def is_valid_link_element(link_element: list):
        """link_element的数据库校验"""
        elements = [ElementManager.get_element_by_id(t['element_id']) for t in link_element]
        # 链路位置相同的网元类型必须相同
        object_type = ''
        for i in range(len(link_element)):
            if i > 0 and link_element[i - 1]['index'] == link_element[i]['index']:
                if elements[i].object_type != object_type:
                    raise errors.InvalidArgument(message=_('存在链路位置相同的不同类型的网元'))
            object_type = elements[i].object_type
        for element in elements:
            if not element.is_linkable():
                raise errors.InvalidArgument(message=_(f'不能在网元{element}上创建新链路'))

    @staticmethod
    def filter_queryset(link_status: list = None):
        qs = LinkManager.get_queryset()

        if link_status is not None:
            qs = qs.filter(link_status__in=link_status)

        return qs


