from django.utils.translation import gettext as _
from link.models import Element, DistriFramePort, DistributionFrame
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
        distriframeport = DistriFramePort.objects.filter(id=id).first()
        if distriframeport is None:
            raise errors.TargetNotExist(message=_('配线架端口不存在'), code='DistriFramePortNotExist')
        return distriframeport
    
    def _generate_default_distriframe_port_number(
        row: int,
        col: int,
        distriframe: DistributionFrame  
    ) -> str:
        return "{distriframe_number}({row},{col})".format(
            distriframe_number=distriframe.number, row=row, col=col)

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

