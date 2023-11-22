from django.utils.translation import gettext as _
from link.models import Element, DistriFramePort, DistributionFrame, ElementLink
from core import errors
from link.managers.element_manager import ElementManager

class DistriFramePortManager:
    @staticmethod
    def get_queryset():
        return DistriFramePort.objects.all()

    @staticmethod
    def get_distriframeport(id: str):
        """
        :raises: DistriFramePortNotExist
        """
        distriframeport = DistriFramePortManager.get_queryset().filter(id=id).first()
        if distriframeport is None:
            raise errors.TargetNotExist(message=_('配线架端口不存在'), code='DistriFramePortNotExist')
        return distriframeport
    
    @staticmethod
    def _generate_default_distriframe_port_number(
        row: int,
        col: int,
        distriframe: DistributionFrame  
    ) -> str:
        return "{distriframe_number}({row},{col})".format(
            distriframe_number=distriframe.number, row=row, col=col)

    @staticmethod
    def create_distriframe_port(
        row: int,
        col: int,
        distriframe: DistributionFrame
    ) -> DistributionFrame:
        distriframe_port_id = DistriFramePort().generate_id()
        element = ElementManager.create_element(object_id=distriframe_port_id, object_type=Element.Type.DISTRIFRAME_PORT)
        distriframe_port = DistriFramePort(
            id=distriframe_port_id,
            number=DistriFramePortManager._generate_default_distriframe_port_number(
                distriframe=distriframe, row=row, col=col),
            row=row,
            col=col,
            distribution_frame=distriframe,
            element=element
        )
        distriframe_port.save(force_insert=True)

    @staticmethod
    def filter_queryset(is_linked:bool = None, distribution_frame_id:str = None):
        qs = DistriFramePortManager.get_queryset()
        if distribution_frame_id is not None:
            qs = qs.filter(distribution_frame_id=distribution_frame_id)
        if is_linked is not None:
            linked_object_id_list = ElementLink.get_linked_object_id_list(object_type=Element.Type.DISTRIFRAME_PORT)
            if is_linked is True:
                qs = qs.filter(id__in=linked_object_id_list)
            else:
                qs = qs.exclude(id__in=linked_object_id_list)
        return qs
