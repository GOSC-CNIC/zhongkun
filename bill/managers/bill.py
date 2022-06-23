from datetime import datetime

from django.utils.translation import gettext as _

from core import errors
from bill.models import PaymentHistory
from utils.model import OwnerType
from vo.managers import VoManager


class PaymentHistoryManager:
    @staticmethod
    def get_queryset():
        return PaymentHistory.objects.all()

    def get_user_payment_history(
            self,
            user,
            _type: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_id: str = None
    ):
        service_ids = [app_service_id, ] if app_service_id else None
        return self.filter_queryset(
            user_id=user.id, _type=_type, time_start=time_start, time_end=time_end, app_service_ids=service_ids
        )

    def get_vo_payment_history(
            self,
            user,
            vo_id: str,
            _type: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_id: str = None
    ):
        """
        :raises: Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        service_ids = [app_service_id, ] if app_service_id else None
        return self.filter_queryset(
            vo_id=vo_id, _type=_type, time_start=time_start, time_end=time_end, app_service_ids=service_ids
        )

    def filter_queryset(
            self,
            user_id: str = None,
            vo_id: str = None,
            _type: str= None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_ids: list = None
    ):
        """
        支付记录查询集

        * user_id和vo_id不能同时查询
        * time_start和time_end必须同时为None 或者同时是有效时间，time_end > time_start

        :param user_id: 所属用户
        :param vo_id: 所属vo组
        :param _type: 支付记录类型
        :param time_start: 支付时间段起（包含）
        :param time_end: 支付时间段止（不包含）
        :param resource_type: 资源类型
        :param app_service_ids: 所属APP服务
        :return:
            QuerySet
        :raises: Error
        """
        if _type and _type not in PaymentHistory.Type.values:
            raise errors.Error(message=_('无效的支付记录类型'))

        if user_id and vo_id:
            raise errors.Error(message=_('不能查询同时属于用户和vo组的支付记录'))

        queryset = self.get_queryset()
        if time_start is not None or time_end is not None:
            if not (time_start and time_end):
                raise errors.Error(message=_('time_start和time_end必须同时是有效时间'))

            if time_start >= time_end:
                raise errors.Error(message=_('时间time_end必须大于time_start'))
            queryset = queryset.filter(payment_time__gte=time_start, payment_time__lt=time_end)

        if app_service_ids:
            if len(app_service_ids) == 1:
                queryset = queryset.filter(app_service_id=app_service_ids[0])
            else:
                queryset = queryset.filter(app_service_id__in=app_service_ids)

        if user_id:
            queryset = queryset.filter(payer_id=user_id, payer_type=OwnerType.USER.value)

        if vo_id:
            queryset = queryset.filter(payer_id=vo_id, payer_type=OwnerType.VO.value)

        if _type:
            queryset = queryset.filter(type=_type)

        return queryset.order_by('-payment_time')
