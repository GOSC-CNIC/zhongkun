from typing import Dict
from datetime import timedelta

from django.utils.translation import gettext as _
from django.utils import timezone as dj_timezone
from django.db.models import Q

from core import errors
from apps.storage.models import ObjectsService
from apps.storage.request import request_service as storage_request_service
from apps.service.models import OrgDataCenterAdminUser


class ObjectsServiceManager:
    @staticmethod
    def get_service_queryset():
        return ObjectsService.objects.select_related('org_data_center__organization').all()

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
        service = ObjectsService.objects.select_related(
            'org_data_center__organization').filter(id=service_id).first()
        if not service:
            raise errors.ServiceNotExist(_('资源提供者服务单元不存在'))

        if service.status != ObjectsService.Status.ENABLE.value:
            raise errors.ServiceStopped(_('资源提供者服务单元停止服务'))

        return service

    @staticmethod
    def get_all_has_perm_qs(user_id):
        return ObjectsService.objects.filter(Q(users__id=user_id) | Q(org_data_center__users__id=user_id)).distinct()

    @staticmethod
    def get_all_has_perm_service(user):
        """
        用户有权限管理的所有存储服务单元
        """
        qs = ObjectsServiceManager.get_all_has_perm_qs(user_id=user.id)
        return qs.select_related('org_data_center__organization')

    @staticmethod
    def get_service_if_admin(user, service_id: str):
        """
        用户是指定云主机服务的管理员

        :return:
            ServiceConfig()     # 是
            None                # 不是
        """
        qs = ObjectsServiceManager.get_all_has_perm_qs(user_id=user.id)
        return qs.filter(id=service_id).first()

    @staticmethod
    def get_service_qs_by_ids(service_ids: list):
        if not service_ids:
            return ObjectsService.objects.none()
        elif len(service_ids) == 1:
            return ObjectsService.objects.filter(id=service_ids[0])
        else:
            return ObjectsService.objects.filter(id__in=service_ids)

    @staticmethod
    def get_has_perm_service_ids(user_id):
        """
        服务单元或数据中管理员权限的单元id
        """
        qs = ObjectsServiceManager.get_all_has_perm_qs(user_id=user_id)
        return qs.values_list('id', flat=True)

    def get_admin_service_qs(self, user):
        if user.is_federal_admin():
            return self.get_service_queryset()

        return self.get_all_has_perm_service(user=user)

    @staticmethod
    def update_service_version(service: ObjectsService):
        try:
            nt = dj_timezone.now()
            if not service.version_update_time or (nt - service.version_update_time) > timedelta(minutes=1):
                r = storage_request_service(service=service, method='get_version')
                if r.version:
                    service.version = r.version
                    service.version_update_time = nt
                    service.save(update_fields=['version', 'version_update_time'])
        except Exception as exc:
            return exc

        return True

    @staticmethod
    def get_service_admins_map(service_ids: list) -> Dict[str, Dict[str, Dict]]:
        """
        服务单元管理员，不包含数据中心管理员

        :return:{
            service_id: {
                "user_id": {"id": "xx", "username": "xxx"}
            }
        }
        """
        queryset = ObjectsService.users.through.objects.filter(
            objectsservice_id__in=service_ids
        ).values('objectsservice_id', 'userprofile_id', 'userprofile__username')
        service_admins_amp = {}
        for i in queryset:
            sv_id = i['objectsservice_id']
            user_info = {'id': i['userprofile_id'], 'username': i['userprofile__username'],
                         'role': OrgDataCenterAdminUser.Role.ADMIN.value}
            if sv_id in service_admins_amp:
                service_admins_amp[sv_id][user_info['id']] = user_info
            else:
                service_admins_amp[sv_id] = {user_info['id']: user_info}

        return service_admins_amp
