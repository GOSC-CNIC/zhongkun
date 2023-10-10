from django.utils.translation import gettext as _

from core import errors
from storage.models import ObjectsService


class ObjectsServiceManager:
    @staticmethod
    def get_service_queryset():
        return ObjectsService.objects.select_related('data_center').all()

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

    @staticmethod
    def get_all_has_perm_service(user):
        """
        用户有权限管理的所有存储服务单元
        """
        return ObjectsService.objects.select_related('data_center').filter(users__id=user.id)
        # return user.object_service_set.select_related('data_center').all()

    @staticmethod
    def get_service_if_admin(user, service_id: str):
        """
        用户是指定云主机服务的管理员

        :return:
            ServiceConfig()     # 是
            None                # 不是
        """
        return ObjectsService.objects.filter(id=service_id, users__id=user.id).first()

    @staticmethod
    def get_service_qs_by_ids(service_ids: list):
        if not service_ids:
            return ObjectsService.objects.none()
        elif len(service_ids) == 1:
            return ObjectsService.objects.filter(id=service_ids[0])
        else:
            return ObjectsService.objects.filter(id__in=service_ids)

    def get_admin_service_qs(self, user):
        if user.is_federal_admin():
            return self.get_service_queryset()

        return self.get_all_has_perm_service(user=user)
