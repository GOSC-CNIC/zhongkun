from django.db.models import Subquery

from .models import ApplyQuota


class ApplyQuotaManager:
    @staticmethod
    def get_apply_queryset():
        return ApplyQuota.objects.all()

    def get_no_deleted_apply_queryset(self):
        queryset = self.get_apply_queryset()
        return queryset.filter(deleted=False)

    def get_admin_apply_queryset(self, user, service_id=None):
        """
        查询用户可管理审批的申请查询集
        """
        services = user.service_set.all()
        queryset = self.get_apply_queryset()
        return queryset.filter(
            service__in=Subquery(services.values_list('id', flat=True))
            ).all()

    @staticmethod
    def filter_queryset(queryset, service_id: str = None, deleted: bool = None,
                        status: list = None):
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        if deleted is not None:
            queryset = queryset.filter(deleted=deleted)

        if status:
            queryset = queryset.filter(status__in=status)

        return queryset

    def filter_user_apply_queryset(self, user, service_id: str = None, deleted: bool = None,
                                   status: list = None):
        """
        过滤用户申请查询集

        :param user: 用户对象
        :param service_id: 服务id
        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param status: 过滤指定状态的申请记录
        """
        queryset = self.get_apply_queryset().filter(user=user)
        return self.filter_queryset(queryset=queryset, service_id=service_id,
                                    deleted=deleted, status=status)

    def admin_filter_apply_queryset(self, user=None, service_id: str = None, deleted: bool = None,
                                    status: list = None):
        """
        管理员过滤申请查询集

        :param user: 管理用户对象,筛选用户用权限管理的申请记录，默认None不筛选
        :param service_id: 服务id
        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param status: 过滤指定状态的申请记录
        """
        if user:
            queryset = self.get_admin_apply_queryset(user)
        else:
            queryset = self.get_apply_queryset()

        return self.filter_queryset(queryset=queryset, service_id=service_id,
                                    deleted=deleted, status=status)
