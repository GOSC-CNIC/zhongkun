from django.utils.translation import gettext as _
from link.models import DistributionFrame, LinkOrg
from core import errors
from django.db import transaction
from link.managers.distriframeport_manager import DistriFramePortManager

class DistriFrameManager:
    @staticmethod
    def get_queryset():
        print(type(DistributionFrame.objects.first().distriframe_distriframeport))
        return DistributionFrame.objects.all()

    @staticmethod
    def get_distriframe(id: str):
        """
        :raises: DistributionFrameNotExist
        """
        distriframe = DistributionFrame.objects.filter(id=id).first()
        if distriframe is None:
            raise errors.TargetNotExist(message=_('配线架不存在'), code='DistributionFrameNotExist')
        return distriframe

    @staticmethod
    def create_distriframe(
            number: str,
            model_type: str,
            row_count: int,
            col_count: int,
            place: str,
            link_org: LinkOrg,
            remarks: str
    ) -> DistributionFrame:
        with transaction.atomic():
            # 创建光缆记录
            distriframe = DistributionFrame(
                number=number,
                model_type=model_type,
                row_count=row_count,
                col_count=col_count,
                place=place,
                remarks=remarks,
                link_org=link_org
            )
            distriframe.save(force_insert=True)
            # 创建光纤记录
            for i in range(1, row_count + 1):
                for j in range(1, col_count + 1):
                    DistriFramePortManager.create_distriframe_port(row=i, col=j, distriframe=distriframe)

        return distriframe
