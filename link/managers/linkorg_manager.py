from django.utils.translation import gettext as _
from link.models import LinkOrg
from core import errors
from service.models import DataCenter

class LinkOrgManager:
    @staticmethod
    def get_queryset():
        return LinkOrg.objects.all()

    @staticmethod
    def get_linkorg(id: str):
        """
        :raises: LinkOrgNotExist
        """
        linkorg = LinkOrg.objects.filter(id=id).first()
        if linkorg is None:
            raise errors.TargetNotExist(message=_('二级机构不存在'), code='LinkOrgNotExist')
        return linkorg

    def create_linkorg(
        data_center: DataCenter,
        name: str,
        remarks: str,
        location: str
    ) -> LinkOrg:
        linkorg = LinkOrg(
            name=name,
            remarks=remarks,
            location=location,
            data_center=data_center
        )
        linkorg.save(force_insert=True)
        return linkorg