from django.utils.translation import gettext as _

from core import errors
from storage.models import ObjectsService


class ObjectsServiceManager:
    @staticmethod
    def get_service_queryset():
        return ObjectsService.objects.all()

    @staticmethod
    def get_service_by_id(_id: str):
        """
        :return: None or ObjectsService()
        """
        return ObjectsService.objects.filter(id=_id).first()

    @staticmethod
    def get_service(service_id: str):
        """
        :raises: Error
        """
        service = ObjectsService.objects.select_related('data_center').filter(id=service_id).first()
        if not service:
            raise errors.ServiceNotExist(_('资源提供者服务单元不存在'))

        if service.status != ObjectsService.Status.ENABLE.value:
            raise errors.ServiceStopped(_('资源提供者服务单元停止服务'))

        return service
