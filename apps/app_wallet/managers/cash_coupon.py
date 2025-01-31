from decimal import Decimal
from typing import List
from datetime import datetime

from django.utils.translation import gettext as _
from django.db import transaction
from django.utils import timezone
from django.db.transaction import TransactionManagementError

from core import errors
from utils.model import OwnerType
from apps.app_vo.managers import VoManager
from apps.app_wallet.models import CashCoupon, CashCouponPaymentHistory, CashCouponActivity, PayAppService
from apps.app_users.models import UserProfile


def get_app_service_by_admin(_id: str, user):
    """
    查询app service，检测用户管理权限

    :rraise: AppServiceNotExist, AccessDenied
    """
    app_service = PayAppService.objects.filter(id=_id).first()
    if app_service is None:
        raise errors.AppServiceNotExist(message=_('App子服务不存在'))

    if user.is_federal_admin():
        return app_service

    if not app_service.user_has_perm(user):
        raise errors.AccessDenied(message=_('你没有此App子服务的权限'))

    return app_service


class CashCouponManager:
    @staticmethod
    def get_queryset():
        return CashCoupon.objects.all()

    def get_cash_coupon(self, coupon_id: str, select_for_update: bool = False, related_fields: list = None):
        """
        :return: CashCoupon() or None
        """
        queryset = self.get_queryset()
        if related_fields:
            queryset = queryset.select_related(*related_fields)

        if select_for_update:
            queryset = queryset.select_for_update()

        return queryset.filter(id=coupon_id).first()

    @staticmethod
    def has_read_perm_cash_coupon(coupon: CashCoupon, user):
        """
        用户是否资源券查询权限

        :return: True
        :raises: Error
        """
        if coupon is None:
            raise errors.NotFound(message=_('资源券不存在'), code='NoSuchCoupon')

        if coupon.status not in [CashCoupon.Status.AVAILABLE.value, CashCoupon.Status.CANCELLED.value]:
            raise errors.NotFound(message=_('资源券不存在'), code='NoSuchCoupon')

        if coupon.owner_type == OwnerType.USER.value:
            if coupon.user_id != user.id:
                raise errors.AccessDenied(message=_('你没有此资源券的访问权限'))
        elif coupon.owner_type == OwnerType.VO.value:
            VoManager().get_has_read_perm_vo(vo_id=coupon.vo_id, user=user)
        else:
            raise errors.ConflictError(message=_('资源券拥有者类型未知'), code='UnknownOwnCoupon')

        return coupon

    @staticmethod
    def has_manage_perm_cash_coupon(coupon: CashCoupon, user):
        """
        用户是否有资源券管理权限

        :return: True
        :raises: Error
        """
        if coupon is None:
            raise errors.NotFound(message=_('资源券不存在'), code='NoSuchCoupon')

        if coupon.status not in [CashCoupon.Status.AVAILABLE.value, CashCoupon.Status.CANCELLED.value]:
            raise errors.NotFound(message=_('资源券不存在'), code='NoSuchCoupon')

        if coupon.owner_type == OwnerType.USER.value:
            if coupon.user_id != user.id:
                raise errors.AccessDenied(message=_('你没有此资源券的访问权限'))
        elif coupon.owner_type == OwnerType.VO.value:
            VoManager().get_has_manager_perm_vo(vo_id=coupon.vo_id, user=user)
        else:
            raise errors.ConflictError(message=_('资源券拥有者类型未知'), code='UnknownOwnCoupon')

        return coupon

    @staticmethod
    def has_admin_perm_cash_coupon(coupon: CashCoupon, user):
        """
        用户是否有资源券管理员权限

        :return: True
        :raises: NotFound，AccessDenied
        """
        if coupon is None:
            raise errors.NotFound(message=_('资源券不存在'), code='NoSuchCoupon')

        if coupon.status not in [
            CashCoupon.Status.AVAILABLE.value, CashCoupon.Status.CANCELLED.value, CashCoupon.Status.WAIT.value
        ]:
            raise errors.NotFound(message=_('资源券不存在'), code='NoSuchCoupon')

        if user.is_federal_admin():
            pass
        elif coupon.app_service:
            if not coupon.app_service.user_has_perm(user):
                raise errors.AccessDenied(message=_('你没有此资源券适用子服务的管理权限'))
        else:
            raise errors.AccessDenied(message=_('此资源券未指定适用子服务，你没有权限管理此资源券。'))

        return coupon

    def get_wait_draw_cash_coupon(self, coupon_id: str, select_for_update: bool = False) -> CashCoupon:
        """
        查询待领取的券
        :raises: Error
        """
        coupon = self.get_cash_coupon(coupon_id, select_for_update)
        if coupon is None:
            raise errors.NotFound(message=_('资源券不存在'), code='NoSuchCoupon')

        self.ensure_wait_draw_cash_coupon(coupon=coupon)
        return coupon

    @staticmethod
    def ensure_wait_draw_cash_coupon(coupon):
        """
        检查确保资源券未领取状态
        """
        if coupon.status == CashCoupon.Status.CANCELLED.value:
            raise errors.ConflictError(message=_('资源券已作废'), code='AlreadyCancelled')

        if coupon.status == CashCoupon.Status.DELETED.value:
            raise errors.ConflictError(message=_('资源券已删除'), code='AlreadyDeleted')

        if (
            coupon.user_id or
            coupon.vo_id or
            coupon.status != CashCoupon.Status.WAIT.value or
            coupon.owner_type != ''
        ):
            raise errors.ConflictError(message=_('资源券已被领取'), code='AlreadyGranted')

    def draw_cash_coupon(self, coupon_id: str, coupon_code: str, user, vo_id: str = None) -> CashCoupon:
        """
        领取资源券
        :raises: Error
        """
        if vo_id:
            vo, m = VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=user)
        else:
            vo = None

        with transaction.atomic():
            coupon = self.get_wait_draw_cash_coupon(coupon_id=coupon_id, select_for_update=True)
            if coupon.coupon_code != coupon_code:
                raise errors.ConflictError(message=_('券验证码错误'), code='InvalidCouponCode')

            return self._grant_coupon_to_user_or_vo(coupon=coupon, user=user, vo=vo)

    @staticmethod
    def _grant_coupon_to_user_or_vo(coupon: CashCoupon, user, vo=None):
        if coupon.app_service is None:
            raise errors.ConflictError(message=_('资源券无效，没有绑定适用的APP子服务。'), code='InvalidCoupon')

        # vo组只能兑换云主机的适用券
        if vo and coupon.app_service.category != PayAppService.Category.VMS_SERVER.value:
            raise errors.ConflictError(
                message=_('绑定的适用APP子服务类型为云主机服务的资源券才允许VO组兑换。'), code='NotAllowToVo')

        coupon.user = user
        coupon.status = CashCoupon.Status.AVAILABLE.value
        coupon.granted_time = timezone.now()
        if vo:
            coupon.vo = vo
            coupon.vo_id = vo.id
            coupon.owner_type = OwnerType.VO.value
        else:
            coupon.vo_id = None
            coupon.owner_type = OwnerType.USER.value

        coupon.save(update_fields=['user_id', 'status', 'granted_time', 'vo_id', 'owner_type'])
        return coupon

    @staticmethod
    def create_wait_draw_coupon(
            app_service_id: str,
            face_value: Decimal,
            effective_time: datetime,
            expiration_time: datetime,
            coupon_num: int,
            issuer: str,
            derive_type: str,
            use_scope: str,
            order_id: str = '',
            activity_id: str = None,
            remark: str = '',
    ):
        """
        创建一个待领取的券

        :coupon_num: 券日编号，大于0有效，其他默认使用当前时间微妙数
        :return:{
            coupon,             # 券对象
            coupon_num: int     # 当前券日编号
        }
        """
        if coupon_num <= 0:
            num = CashCouponManager.get_date_coupon_count(date=timezone.now().date())
            coupon_num = num + 1

        for i in range(6):
            try:
                coupon = CashCoupon.create_wait_draw_coupon(
                    face_value=face_value,
                    effective_time=effective_time,
                    expiration_time=expiration_time,
                    app_service_id=app_service_id,
                    activity_id=activity_id,
                    coupon_num=coupon_num,
                    issuer=issuer,
                    remark=remark,
                    use_scope=use_scope,
                    order_id=order_id,
                    derive_type=derive_type
                )
                return coupon, coupon_num
            except Exception as exc:
                # 如果此函数是在一个事务中执行的，不再重试，事务中发生错误后是无法执行数据库查询的，会抛出TransactionManagementError
                try:
                    num = CashCouponManager.get_date_coupon_count(date=timezone.now().date())
                except TransactionManagementError as e:
                    raise exc
                if num > coupon_num:
                    coupon_num = num

                coupon_num += 1
                continue

        # 再尝试一次随机
        coupon = CashCoupon.create_wait_draw_coupon(
            face_value=face_value,
            effective_time=effective_time,
            expiration_time=expiration_time,
            app_service_id=app_service_id,
            activity_id=activity_id,
            coupon_num=coupon_num,
            issuer=issuer,
            remark=remark,
            use_scope=use_scope,
            order_id=order_id,
            derive_type=derive_type
        )
        return coupon, coupon_num

    def create_one_coupon_to_user_or_vo(
            self, user, vo,
            app_service_id: str,
            face_value: Decimal,
            effective_time: datetime,
            expiration_time: datetime,
            issuer: str,
            activity_id: str = None,
            remark: str = '',
            use_scope: str = CashCoupon.UseScope.SERVICE_UNIT.value,
            order_id: str = '',
            derive_type: str = CashCoupon.DeriveType.OTHER.value,
    ):
        """
        创建一个券，并发放给指定user或vo

        vo is None: 发给user
        vo is not None: 发给vo，此时user为领取人
        """
        num = CashCouponManager.get_date_coupon_count(date=timezone.now().date())
        with transaction.atomic():
            coupon, coupon_num = self.create_wait_draw_coupon(
                app_service_id=app_service_id,
                face_value=face_value,
                effective_time=effective_time,
                expiration_time=expiration_time,
                activity_id=activity_id,
                coupon_num=num + 1,
                issuer=issuer, remark=remark,
                use_scope=use_scope, order_id=order_id,
                derive_type=derive_type
            )
            self.ensure_wait_draw_cash_coupon(coupon=coupon)
            self._grant_coupon_to_user_or_vo(coupon=coupon, user=user, vo=vo)

        return coupon

    @staticmethod
    def _filter_cash_coupon_queryset(
            queryset, app_service_id: str = None, valid: str = None,
            app_service_category: str = None
    ):
        """
        :valid: notyet(未起效), valid(有效期内), expired(已过期)；None（不筛选）
        """
        if app_service_id:
            queryset = queryset.filter(app_service_id=app_service_id)

        if app_service_category:
            queryset = queryset.filter(app_service__category=app_service_category)

        if valid:
            now = timezone.now()
            if valid == 'valid':
                queryset = queryset.filter(effective_time__lt=now, expiration_time__gt=now)
            elif valid == 'notyet':
                queryset = queryset.filter(effective_time__gt=now)
            elif valid == 'expired':
                queryset = queryset.filter(expiration_time__lte=now)
            else:
                raise errors.Error(message=_('参数“valid”值无效'))

        return queryset

    def get_user_cash_coupon_queryset(
            self, user_id: str, app_service_id: str = None, valid: str = None,
            app_service_category: str = None
    ):
        """
        :valid: notyet(未起效), valid(有效期内), expired(已过期)；None（不筛选）
        """
        queryset = self.get_queryset()
        queryset = queryset.filter(
            user_id=user_id, owner_type=OwnerType.USER.value,
            status=CashCoupon.Status.AVAILABLE.value
        ).select_related('vo', 'user', 'activity', 'app_service')

        return self._filter_cash_coupon_queryset(
            queryset=queryset, app_service_id=app_service_id,
            valid=valid, app_service_category=app_service_category
        )

    def get_vo_cash_coupon_queryset(
            self, user, vo_id: str, app_service_id: str = None, valid: str = None,
            app_service_category: str = None
    ):
        """
        :valid: notyet(未起效), valid(有效期内), expired(已过期)；None（不筛选）
        :raises: Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        queryset = self.get_queryset()
        queryset = queryset.filter(
            vo_id=vo_id, owner_type=OwnerType.VO.value,
            status=CashCoupon.Status.AVAILABLE.value
        ).select_related('vo', 'user', 'activity', 'app_service')

        return self._filter_cash_coupon_queryset(
            queryset=queryset, app_service_id=app_service_id,
            valid=valid, app_service_category=app_service_category
        )

    def delete_cash_coupon(self, coupon_id: str, user, force: bool = False):
        """
        删除资源券
        :raises: Error
        """
        coupon = self.get_cash_coupon(coupon_id=coupon_id)
        self.has_manage_perm_cash_coupon(coupon=coupon, user=user)

        if not force:
            if (
                coupon.status == CashCoupon.Status.AVAILABLE.value and
                coupon.expiration_time > timezone.now()
            ):    # 未过期
                if coupon.balance > Decimal(0):
                    raise errors.ConflictError(message=_('资源券有剩余余额未消费'), code='BalanceRemain')

        coupon.status = CashCoupon.Status.DELETED.value
        coupon.save(update_fields=['status'])
        return coupon

    def admin_delete_cash_coupon(self, coupon_id: str, user):
        """
        管理员删除资源券
        :raises: Error
        """
        coupon: CashCoupon = self.get_cash_coupon(coupon_id=coupon_id, related_fields=['app_service'])
        self.has_admin_perm_cash_coupon(coupon=coupon, user=user)
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

        :param queryset: 资源券查询集
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
                raise errors.NotFound(message=_('资源券%(value)s不存在') % {'value': c_id}, code='NoSuchCoupon')

            coupon = coupons_dict[c_id]
            if coupon.status != CashCoupon.Status.AVAILABLE.value:
                raise errors.ConflictError(message=_('资源券%(value)s无效') % {'value': c_id}, code='NotAvailable')

            if coupon.effective_time and coupon.effective_time > now:
                raise errors.ConflictError(
                    message=_('资源券%(value)s未到生效时间') % {'value': c_id}, code='NotEffective')

            if not coupon.expiration_time or coupon.expiration_time < now:
                raise errors.ConflictError(message=_('资源券%(value)s已过期') % {'value': c_id}, code='ExpiredCoupon')

            coupons.append(coupon)

        return coupons

    @staticmethod
    def sorting_usable_coupons(coupons: List[CashCoupon], app_service_id: str, order_id: str = ''):
        """
        分拣适用指定服务和订单的券

        不指定订单编号时，使用范围为“指定订单”的券为不可用
        """
        # 适用的券
        usable_coupons = []
        unusable_coupons = []
        for coupon in coupons:
            if CashCouponManager.is_usable_coupon(coupon=coupon, app_service_id=app_service_id, order_id=order_id):
                usable_coupons.append(coupon)
            else:
                unusable_coupons.append(coupon)

        return usable_coupons, unusable_coupons

    @staticmethod
    def is_usable_coupon(coupon: CashCoupon, app_service_id: str, order_id: str = '') -> bool:
        """
        判定券是否适用 指定结算单元 和 订单

        * 不指定订单编号时，使用范围为“指定订单”的券为不可用
        """
        # 结算单元不一致，不可用
        if app_service_id != coupon.app_service_id:
            return False

        # 全结算单元券，可用
        if coupon.use_scope == CashCoupon.UseScope.SERVICE_UNIT.value:
            return True
        elif coupon.use_scope == CashCoupon.UseScope.ORDER.value:
            # 指定订单编号的券，订单编号一致 可用
            if order_id and coupon.order_id == order_id:
                return True
            else:
                return False

        return False

    def get_cash_coupon_payment_queryset(self, coupon_id: str, user):
        """
        资源券扣费记录查询集

        :return: QuerySet
        :raises: Error
        """
        coupon = self.get_cash_coupon(coupon_id=coupon_id)
        self.has_read_perm_cash_coupon(coupon=coupon, user=user)
        queryset = CashCouponPaymentHistory.objects.select_related(
            'payment_history', 'refund_history'
        ).filter(cash_coupon_id=coupon.id)
        return queryset

    def admin_get_cash_coupon_payment_queryset(self, coupon_id: str, user):
        """
        管理员查询资源券扣费记录查询集

        :return: QuerySet
        :raises: Error
        """
        coupon = self.get_cash_coupon(coupon_id=coupon_id)
        self.has_admin_perm_cash_coupon(coupon=coupon, user=user)
        queryset = CashCouponPaymentHistory.objects.select_related(
            'payment_history', 'refund_history'
        ).filter(cash_coupon_id=coupon.id)
        return queryset

    def admin_list_coupon_queryset(
            self, user: UserProfile, template_id: str = None, app_service_id: str = None, status: str = None,
            valid: str = None, issuer: str = None, redeemer: str = None,
            createtime_start: datetime = None, createtime_end: datetime = None, coupon_id: str = None,
            owner_type: str = None, vo_id: str = None
    ):
        """
        :valid: notyet(未起效), valid(有效期内), expired(已过期)；None（不筛选）
        """
        if user.is_federal_admin():
            app_service_ids = [app_service_id] if app_service_id else None
            return self.filter_coupon_queryset(
                template_id=template_id, app_service_ids=app_service_ids, status=status, valid=valid,
                issuer=issuer, redeemer=redeemer, createtime_start=createtime_start, createtime_end=createtime_end,
                coupon_id=coupon_id, owner_type=owner_type, vo_id=vo_id
            )

        if template_id:
            template = CashCouponActivityManager.get_activity(activity_id=template_id)
            if template is None:
                raise errors.NotFound(message=_('券活动模板不存在'))

            # check permission
            if not CashCouponActivityManager.has_coupon_template_perm(activity=template, user=user):
                raise errors.AccessDenied(message=_('你没有此券模板的权限'))

        if app_service_id:
            get_app_service_by_admin(_id=app_service_id, user=user)
            app_service_ids = [app_service_id] if app_service_id else None
        else:
            app_service_ids = PayAppService.objects.filter(users__id=user.id).values_list('id', flat=True)
            app_service_ids = list(app_service_ids)
            if not app_service_ids:
                return CashCoupon.objects.none()

        return self.filter_coupon_queryset(
            template_id=template_id, app_service_ids=app_service_ids, status=status, valid=valid,
            issuer=issuer, redeemer=redeemer, createtime_start=createtime_start, createtime_end=createtime_end,
            coupon_id=coupon_id, owner_type=owner_type, vo_id=vo_id
        )

    @staticmethod
    def filter_coupon_queryset(
            template_id: str = None, app_service_ids: list = None, status: str = None, valid: str = None,
            issuer: str = None, redeemer: str = None,
            createtime_start: datetime = None, createtime_end: datetime = None, coupon_id: str = None,
            owner_type: str = None, vo_id: str = None
    ):
        """
        :valid: notyet(未起效), valid(有效期内), expired(已过期)；None（不筛选）
        """
        queryset = CashCoupon.objects.select_related('app_service', 'activity').all()
        if coupon_id:
            queryset = queryset.filter(id=coupon_id)

        if template_id:
            queryset = queryset.filter(activity_id=template_id)

        if app_service_ids:
            if len(app_service_ids) == 1:
                queryset = queryset.filter(app_service_id=app_service_ids[0])
            else:
                queryset = queryset.filter(app_service_id__in=app_service_ids)

        if status:
            queryset = queryset.filter(status=status)

        if valid:
            now = timezone.now()
            if valid == 'valid':
                queryset = queryset.filter(effective_time__lt=now, expiration_time__gt=now)
            elif valid == 'notyet':
                queryset = queryset.filter(effective_time__gt=now)
            elif valid == 'expired':
                queryset = queryset.filter(expiration_time__lte=now)
            else:
                raise errors.Error(message=_('参数“valid”值无效'))

        if issuer is not None:
            queryset = queryset.filter(issuer=issuer)

        if redeemer:
            redeemer_user = UserProfile.objects.filter(username=redeemer).first()
            if redeemer_user is None:
                raise errors.UserNotExist(message=_('指定的兑换人不存在'))

            queryset = queryset.filter(user_id=redeemer_user.id)

        if createtime_start:
            queryset = queryset.filter(creation_time__gte=createtime_start)

        if createtime_end:
            queryset = queryset.filter(creation_time__lt=createtime_end)

        if vo_id:
            queryset = queryset.filter(vo_id=vo_id)
            if not owner_type:
                owner_type = OwnerType.VO.value

        if owner_type:
            queryset = queryset.filter(owner_type=owner_type)

        return queryset

    @staticmethod
    def get_date_coupon_count(date):
        return CashCoupon.objects.filter(creation_time__date=date).count()


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

        coupon, coupon_num = self.clone_coupon(activity=activity, coupon_num=0, issuer=user.username)
        return coupon

    @staticmethod
    def has_coupon_template_perm(activity: CashCouponActivity, user):
        """
        是否有券模板的访问权限，是否有权限从模板创建券
        """
        if not activity.app_service:
            return False

        return activity.app_service.user_has_perm(user)

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
            coupon_num = 0
            for index in range(1, count + 1):
                try:
                    c, coupon_num = self.clone_coupon(activity=activity, coupon_num=coupon_num, issuer=user.username)
                    coupon_num += 1
                except Exception as e:
                    raise e
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

    @staticmethod
    def clone_coupon(activity, coupon_num: int, issuer: str):
        """
        尝试多次尽量确保创建券成功

        :param activity: 券模板
        :param coupon_num: 券日编号，大于0有效，其他默认使用当前时间微妙数
        :param issuer: 券发放人
        :return:{
            coupon,             # 券对象
            coupon_num: int     # 当前券日编号
        }

        :raises: Exception
        """
        coupon, coupon_num = CashCouponManager.create_wait_draw_coupon(
            app_service_id=activity.app_service_id,
            face_value=activity.face_value,
            effective_time=activity.effective_time,
            expiration_time=activity.expiration_time,
            coupon_num=coupon_num,
            activity_id=activity.id,
            issuer=issuer,
            use_scope=CashCoupon.UseScope.SERVICE_UNIT.value,
            order_id='',
            derive_type=CashCoupon.DeriveType.OTHER.value
        )
        return coupon, coupon_num
