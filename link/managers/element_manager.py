from django.utils.translation import gettext as _
from link.models import Element, ElementLink, ElementDetailData
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
        element = ElementManager.get_queryset().filter(id=id).first()
        if element is None:
            raise errors.TargetNotExist(message=_('网元不存在'), code='ElementNotExist')
        return element

    @staticmethod
    def get_element_by_object(
            object_type: str,
            object_id: str,
    ) -> Element:
        element = ElementManager.get_queryset().filter(object_id=object_id, object_type=object_type).first()
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
    def get_element_detail_data_by_id(
        id: str,
    ) -> ElementDetailData:
        from link.managers.opticalfiber_manager import OpticalFiberManager
        from link.managers.connectorbox_manager import ConnectorBoxManager
        from link.managers.distriframeport_manager import DistriFramePortManager
        from link.managers.leaseline_manager import LeaseLineManager
        element = ElementManager.get_element_by_id(id=id)
        type = element.object_type
        if type == Element.Type.LEASE_LINE:
            lease = LeaseLineManager.get_leaseline(id=element.object_id)
            return ElementDetailData(type=type, lease=lease)
        elif type == Element.Type.OPTICAL_FIBER:
            fiber = OpticalFiberManager.get_opticalfiber(id=element.object_id)
            return ElementDetailData(type=type, fiber=fiber)
        elif type == Element.Type.DISTRIFRAME_PORT:
            port = DistriFramePortManager.get_distriframeport(id=element.object_id)
            return ElementDetailData(type=type, port=port)
        elif type == Element.Type.CONNECTOR_BOX:
            box = ConnectorBoxManager.get_connectorbox(id=element.object_id)
            return ElementDetailData(type=type, box=box)
        else:
            raise errors.Error(message=_(f'无法识别的网元种类, type: {type}'))
