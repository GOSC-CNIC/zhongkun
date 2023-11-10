from django.utils.translation import gettext as _
from link.models import ConnectorBox, Element
from core import errors
from link.managers.element_manager import ElementManager, ElementLink
from django.db import transaction

class ConnectorBoxManager:
    @staticmethod
    def get_queryset():
        return ConnectorBox.objects.all()

    @staticmethod
    def get_connectorbox(id: str):
        """
        :raises: ConnectorBoxNotExist
        """
        connectorbox = ConnectorBoxManager.get_queryset().filter(id=id).first()
        if connectorbox is None:
            raise errors.TargetNotExist(message=_('光缆熔纤包不存在'), code='ConnectorBoxNotExist')
        return connectorbox

    @staticmethod
    def create_connectorbox(
            number: str,
            place: str,
            remarks: str,
            location: str,
    ) -> ConnectorBox:
        with transaction.atomic():
            connectorbox_id = ConnectorBox().generate_id()
            element = ElementManager.create_element(object_id=connectorbox_id, object_type=Element.Type.CONNECTOR_BOX)
            connectorbox = ConnectorBox(
                id=connectorbox_id,
                number=number,
                place=place,
                remarks=remarks,
                location=location,
                element=element
            )
            connectorbox.save(force_insert=True)
        return connectorbox

    @staticmethod
    def filter_queryset(is_linked: bool = None):
        qs = ConnectorBoxManager.get_queryset()
        if is_linked is not None:
            linked_element_id_list = ElementLink.get_linked_element_id_list()
            if is_linked is True:
                qs = qs.filter(element_id__in=linked_element_id_list)
            else:
                qs = qs.exclude(element_id__in=linked_element_id_list)
        return qs
