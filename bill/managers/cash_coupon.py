from decimal import Decimal
from typing import List

from django.utils.translation import gettext as _
from django.db import transaction
from django.utils import timezone

from core import errors
from utils.model import OwnerType
from vo.managers import VoManager
from bill.models import CashCoupon, CashCouponPaymentHistory, CashCouponActivity, PayAppService
from users.models import UserProfile


class CashCouponManager:
    @staticmethod
    def get_queryset():
        return CashCoupon.objects.all()

    def get_cash_coupon(self, coupon_id: str, select_for_update: bool = False):
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

    def get_user_cash_coupon_queryset(self, user_id: str, app_service_id: str = None, available: bool = None):
        queryset = self.get_queryset()
        queryset = queryset.filter(
            user_id=user_id, owner_type=OwnerType.USER.value,
            status=CashCoupon.Status.AVAILABLE.value
        ).select_related('vo', 'user', 'activity', 'app_service')

        if app_service_id:
            queryset = queryset.filter(app_service_id=app_service_id)

        if available:
            now = timezone.now()
            queryset = queryset.filter(effective_time__lt=now, expiration_time__gt=now)

        return queryset

    def get_vo_cash_coupon_queryset(self, user, vo_id: str, app_service_id: str = None, available: bool = None):
        """
        :raises: Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        queryset = self.get_queryset()
        queryset = queryset.filter(
            vo_id=vo_id, owner_type=OwnerType.VO.value,
            status=CashCoupon.Status.AVAILABLE.value
        ).select_related('vo', 'user', 'activity', 'app_service')

        if app_service_id:
            queryset = queryset.filter(app_service_id=app_service_id)

        if available:
            now = timezone.now()
            queryset = queryset.filter(effective_time__lt=now, expiration_time__gt=now)

        return queryset

    def delete_cash_coupon(self, coupon_id: str, user, force: bool = False):
        """
        删除代金券
        :raises: Error
        """
        coupon = self.get_cash_coupon(coupon_id=coupon_id)
        if coupon is None:
            raise errors.NotFound(message=_('代金券不存在'), code='NoSuchCoupon')

        if coupon.status not in [CashCoupon.Status.AVAILABLE.value, CashCoupon.Status.CANCELLED.value]:
            raise errors.NotFound(message=_('代金券不存在'), code='NoSuchCoupon')

        if coupon.owner_type == OwnerType.USER.value:
            if coupon.user_id != user.id:
                raise errors.AccessDenied(message=_('你没有此代金券的访问权限'))
        elif coupon.owner_type == OwnerType.VO.value:
            VoManager().get_has_manager_perm_vo(vo_id=coupon.vo_id, user=user)
        else:
            raise errors.ConflictError(message=_('代金券拥有者类型未知'), code='UnknownOwnCoupon')

        if not force:
            if (
                coupon.status == CashCoupon.Status.AVAILABLE.value and
                coupon.expiration_time > timezone.now()
            ):    # 未过期
                if coupon.balance > Decimal(0):
                    raise errors.ConflictError(message=_('代金券有剩余余额未消费'), code='BalanceRemain')

        coupon.status = CashCoupon.Status.DELETED.value
        coupon.save(update_fields=['status'])
        return coupon

    def get_user_cash_coupons(
            self, user_id: str, coupon_ids: list = None, select_for_update: bool = False
    ) -> List[CashCoupon]:
        """
        指定coupon_ids按coupon_ids排序，否者按券过期时间先后排序

        :param user_id: 查询此用户的券
        :param coupon_ids: 查询指定id的券；None(不指定券，查所有券)；[](空，指定不使用券)；
        :param select_for_update: True(需要在事务中使用)
        :return:
            [CashCoupon(),]

        :raises: Error
        """
        return self._get_cash_coupons(
            queryset=CashCoupon.objects.filter(owner_type=OwnerType.USER.value, user_id=user_id),
            coupon_ids=coupon_ids,
            select_for_update=select_for_update
        )

    def get_vo_cash_coupons(
            self, vo_id: str, coupon_ids: list = None, select_for_update: bool = False
    ) -> List[CashCoupon]:
        """
        指定coupon_ids按coupon_ids排序，否者按券过期时间先后排序

        :param vo_id: 查询此vo的券
        :param coupon_ids: 查询指定id的券；None(不指定券，查所有券)；[](空，指定不使用券)；
        :param select_for_update: True(需要在事务中使用)
        :return:
            [CashCoupon(),]

        :raises: Error
        """
        return self._get_cash_coupons(
            queryset=CashCoupon.objects.filter(owner_type=OwnerType.VO.value, vo_id=vo_id),
            coupon_ids=coupon_ids,
            select_for_update=select_for_update
        )

    @staticmethod
    def _get_cash_coupons(queryset, coupon_ids: list, select_for_update: bool = False):
        """
        查询有效可用的券

        指定coupon_ids按coupon_ids排序，否者按券过期时间先后排序

        :param queryset: 代金券查询集
        :param coupon_ids: 查询指定id的券；None(不指定券，查所有券)；[](空，指定不使用券)；
        :param select_for_update: True(需要在事务中使用)
        :return:
            [CashCoupon(),]

        :raises: Error
        """
        if coupon_ids == []:
            return []

        now = timezone.now()
        coupons_qs = queryset.order_by('expiration_time')

        if select_for_update:
            coupons_qs = coupons_qs.select_for_update()

        if not coupon_ids:
            coupons_qs = coupons_qs.filter(
                status=CashCoupon.Status.AVAILABLE.value,
                balance__gt=Decimal(0),
                effective_time__lt=now,
                expiration_time__gt=now
            )
            try:
                return list(coupons_qs)
            except Exception as e:
                raise errors.Error(message=str(e))

        coupons_qs = coupons_qs.filter(id__in=coupon_ids)
        try:
            coupons_dict = {c.id: c for c in coupons_qs}
        except Exception as e:
            raise errors.Error(message=str(e))

        coupons = []
        for c_id in coupon_ids:
            if c_id not in coupons_dict:
                raise errors.NotFound(message=_('代金券%(value)s不存在') % {'value': c_id}, code='NoSuchCoupon')

            coupon = coupons_dict[c_id]
            if coupon.status != CashCoupon.Status.AVAILABLE.value:
                raise errors.ConflictError(message=_('代金券%(value)s无效') % {'value': c_id}, code='NotAvailable')

            if coupon.effective_time and coupon.effective_time > now:
                raise errors.ConflictError(
                    message=_('代金券%(value)s未到生效时间') % {'value': c_id}, code='NotEffective')

            if not coupon.expiration_time or coupon.expiration_time < now:
                raise errors.ConflictError(message=_('代金券%(value)s已过期') % {'value': c_id}, code='ExpiredCoupon')

            coupons.append(coupon)

        return coupons

    @staticmethod
    def sorting_usable_coupons(coupons: List[CashCoupon], app_service_id: str):
        """
        分拣适用指定服务的券
        """
        # 适用的券
        usable_coupons = []
        unusable_coupons = []
        for coupon in coupons:
            if app_service_id == coupon.app_service_id:
                usable_coupons.append(coupon)
            else:
                unusable_coupons.append(coupon)

        return usable_coupons, unusable_coupons

    def get_cash_coupon_payment_queryset(self, coupon_id: str, user):
        """
        代金券扣费记录查询集

        :return: QuerySet
        :raises: Error
        """
        coupon = self.get_cash_coupon(coupon_id=coupon_id)
        if coupon is None:
            raise errors.NotFound(message=_('代金券不存在'), code='NoSuchCoupon')

        if coupon.status not in [CashCoupon.Status.AVAILABLE.value, CashCoupon.Status.CANCELLED.value]:
            raise errors.NotFound(message=_('代金券不存在'), code='NoSuchCoupon')

        if coupon.owner_type == OwnerType.USER.value:
            if coupon.user_id != user.id:
                raise errors.AccessDenied(message=_('你没有此代金券的访问权限'))
        elif coupon.owner_type == OwnerType.VO.value:
            VoManager().get_has_read_perm_vo(vo_id=coupon.vo_id, user=user)
        else:
            raise errors.ConflictError(message=_('代金券拥有者类型未知'), code='UnknownOwnCoupon')

        queryset = CashCouponPaymentHistory.objects.select_related('payment_history').filter(cash_coupon_id=coupon.id)
        return queryset

    def admin_list_coupon_queryset(self, user: UserProfile, template_id: str = None, app_service_id: str = None, status: str = None):
        if user.is_federal_admin():
            return self.filter_coupon_queryset(
                template_id=template_id, app_service_id=app_service_id, status=status
            )

        if not template_id and not app_service_id:
            raise errors.AccessDenied(message=_('参数“template_id”和“app_service_id”必须指定一个'))

        if template_id:
            template = CashCouponActivityManager.get_activity(activity_id=template_id)
            if template is None:
                raise errors.NotFound(message=_('券活动模板不存在'))

            # check permission
            if not CashCouponActivityManager.has_coupon_template_perm(activity=template, user=user):
                raise errors.AccessDenied(message=_('你没有此券模板的权限'))

        if app_service_id:
            app_service = PayAppService.objects.filter(id=app_service_id).first()
            if app_service is None:
                raise errors.NotFound(message=_('App子服务不存在'))

            if app_service.user_id != user.id:
                raise errors.AccessDenied(message=_('你没有此App子服务的权限'))

            service = app_service.service
            if service is None:
                raise errors.AccessDenied(message=_('你没有此App子服务的权限'))

            if not service.user_has_perm(user):
                raise errors.AccessDenied(message=_('你没有此App子服务的权限'))

        return self.filter_coupon_queryset(template_id=template_id, app_service_id=app_service_id, status=status)

    @staticmethod
    def filter_coupon_queryset(template_id: str = None, app_service_id: str = None, status: str = None):
        queryset = CashCoupon.objects.select_related('app_service', 'activity').all()
        if template_id:
            queryset = queryset.filter(activity_id=template_id)

        if app_service_id:
            queryset = queryset.filter(app_service_id=app_service_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset


class CashCouponActivityManager:
    @staticmethod
    def get_queryset():
        return CashCouponActivity.objects.all()

    @staticmethod
    def get_activity(activity_id: str) -> CashCouponActivity:
        return CashCouponActivity.objects.select_related('app_service').filter(id=activity_id).first()

    def clone_coupon_from_template(self, activity_id: str, user) -> CashCoupon:
        """
        从券活动/模板克隆一个券

        :raises: Error
        """
        activity = self.get_activity(activity_id)
        if activity is None:
            raise errors.NotFound(message=_('券活动模板不存在'))

        # check permission
        if not self.has_coupon_template_perm(activity=activity, user=user):
            raise errors.AccessDenied(message=_('你没有此券模板的券的发放权限'))

        coupon = activity.clone_coupon()
        return coupon

    @staticmethod
    def has_coupon_template_perm(activity: CashCouponActivity, user):
        """
        是否有券模板的访问权限，是否有权限从模板创建券
        """
        if not activity.app_service:
            return False

        if activity.app_service.user_id == user.id:
            return True

        service = activity.app_service.service
        if service is None:
            return False

        return service.user_has_perm(user)

    def create_coupons_for_template(self, activity_id: str, user, max_count: int = 1000):
        """
        为券活动/模板创建券

        :param activity_id: 券模板/活动id
        :param user:
        :param max_count: 本次券最大发放数量
        :return:
            (
                CashCouponActivity(),
                count,          # 本次生成券数量
                error           # None or Error(),是否发生错误
            )
        :raises: Error
        """
        activity = self.get_activity(activity_id)
        if activity is None:
            raise errors.NotFound(message=_('券活动模板不存在'))

        if activity.grant_status == CashCouponActivity.GrantStatus.COMPLETED.value:
            raise errors.ConflictError(message=_('已发放完成状态券模板不允许再创建券'))

        granted_count = CashCoupon.objects.filter(activity_id=activity.id).count()
        if activity.grant_total <= granted_count:
            raise errors.ConflictError(message=_('发放的券数量已达到券模板规定的发放数量'))

        # 券模板的有效性
        try:
            activity.validate_availability()
        except errors.Error as exc:
            raise errors.ConflictError(message=_('券模板可用性检验未通过，不能生成券') + str(exc))

        # check permission
        if not self.has_coupon_template_perm(activity=activity, user=user):
            raise errors.AccessDenied(message=_('你没有此券模板的券的发放权限'))

        count = min(activity.grant_total - granted_count, max_count)
        index = 0
        raise_exc = None
        try:
            for index in range(1, count + 1):
                activity.clone_coupon()
        except Exception as exc:
            raise_exc = exc

        granted_count = granted_count + index
        if granted_count >= activity.grant_total:
            activity.grant_status = CashCouponActivity.GrantStatus.COMPLETED.value
        else:
            activity.grant_status = CashCouponActivity.GrantStatus.GRANT.value

        activity.granted_count = granted_count
        activity.save(update_fields=['granted_count', 'grant_status'])

        return activity, index, raise_exc
