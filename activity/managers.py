from django.utils.translation import gettext as _
from django.db import transaction
from django.utils import timezone

from core import errors
from utils.model import OwnerType
from vo.managers import VoManager
from .models import CashCoupon


class CashCouponManager:
    @staticmethod
    def get_queryset():
        return CashCoupon.objects.all()

    def get_cash_coupon(self, coupon_id: str, select_for_update: bool = False) -> CashCoupon:
        """
        :return: CashCoupon() or None
        """
        queryset = self.get_queryset()
        if select_for_update:
            queryset = queryset.select_for_update()

        return queryset.filter(id=coupon_id).first()

    def get_wait_draw_cash_coupon(self, coupon_id: str, select_for_update: bool = False) -> CashCoupon:
        """
        查询待领取的券
        :raises: Error
        """
        coupon = self.get_cash_coupon(coupon_id, select_for_update)
        if coupon is None:
            raise errors.NotFound(message=_('代金券不存在'), code='NoSuchCoupon')

        if coupon.status == CashCoupon.Status.CANCELLED.value:
            raise errors.ConflictError(message=_('代金券已作废'), code='AlreadyCancelled')

        if coupon.status == CashCoupon.Status.DELETED.value:
            raise errors.ConflictError(message=_('代金券已删除'), code='AlreadyDeleted')

        if (
            coupon.user_id or
            coupon.vo_id or
            coupon.status != CashCoupon.Status.WAIT.value or
            coupon.owner_type != ''
        ):
            raise errors.ConflictError(message=_('代金券已被领取'), code='AlreadyGranted')

        return coupon

    def draw_cash_coupon(self, coupon_id: str, coupon_code: str, user, vo_id: str = None) -> CashCoupon:
        """
        领取代金券
        :raises: Error
        """
        vo = None
        if vo_id:
            vo, m = VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=user)

        with transaction.atomic():
            coupon = self.get_wait_draw_cash_coupon(coupon_id=coupon_id, select_for_update=True)
            if coupon.coupon_code != coupon_code:
                raise errors.ConflictError(message=_('券验证码错误'), code='InvalidCouponCode')

            coupon.user = user
            coupon.status = CashCoupon.Status.AVAILABLE.value
            coupon.granted_time = timezone.now()
            if vo_id:
                coupon.vo = vo
                coupon.vo_id = vo_id
                coupon.owner_type = OwnerType.VO.value
            else:
                coupon.vo_id = None
                coupon.owner_type = OwnerType.USER.value

            coupon.save(update_fields=['user_id', 'status', 'granted_time', 'vo_id', 'owner_type'])

        return coupon

    def get_user_cash_coupon_queryset(self, user_id: str, available: bool = None):
        queryset = self.get_queryset()
        queryset = queryset.filter(
            user_id=user_id, owner_type=OwnerType.USER.value,
            status=CashCoupon.Status.AVAILABLE.value
        ).select_related('vo', 'user', 'activity', 'service')

        if available:
            now = timezone.now()
            queryset = queryset.filter(effective_time__lt=now, expiration_time__gt=now)

        return queryset

    def get_vo_cash_coupon_queryset(self, user, vo_id: str, available: bool = None):
        """
        :raises: Error
        """
        VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=user)
        queryset = self.get_queryset()
        queryset = queryset.filter(
            vo_id=vo_id, owner_type=OwnerType.VO.value,
            status=CashCoupon.Status.AVAILABLE.value
        ).select_related('vo', 'user', 'activity', 'service')

        if available:
            now = timezone.now()
            queryset = queryset.filter(effective_time__lt=now, expiration_time__gt=now)

        return queryset
