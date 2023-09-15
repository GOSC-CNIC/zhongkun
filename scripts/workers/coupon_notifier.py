from decimal import Decimal
from datetime import timedelta, datetime

from django.utils import timezone
from django.db.models import Q

from bill.models import CashCoupon
from users.models import Email
from vo.models import VirtualOrganization, VoMember
from utils.model import OwnerType

from . import config_logger


class MessageTemplate:
    TEMPLATE_BODY = """
你好，%(hello_to)s:

%(message)s

谢谢
中国科技云一体化云服务平台(https://service.cstcloud.cn)
"""

    SUBJECT_EXPIRE = '资源券过期通知'
    SUBJECT_INSUFFICIENT = '资源券余额不足通知'
    SUBJECT_EXPIRE_INSUFFICIENT = '资源券即将过期或券余额不足通知'
    YOUR_EXPIRE_MESSAHE = "你的资源券即将过期。"
    YOUR_INSUFFICIENT_MESSAHE = "你的资源券余额不足。"
    YOUR_EXPIRE_INSUFFICIENT_MESSAHE = "你的资源券即将过期，或资源券余额不足。"
    VO_EXPIRE_MESSAHE = "项目组的资源券即将过期。"
    VO_INSUFFICIENT_MESSAHE = "项目组的资源券余额不足。"
    VO_EXPIRE_INSUFFICIENT_MESSAHE = "项目组的资源券即将过期，或资源券余额不足。"
    TEMPLATE_COUPON_MESSAGE = "资源券编号为 %(coupon_id)s ，余额为 %(coupon_balance)s 点，过期时间为 %(expire_time)s。"

    def build_notice_message(self, hello_to: str, notice: str, coupon_id: str, coupon_balance: str, expire_time: str):
        coupon_msg = self.TEMPLATE_COUPON_MESSAGE % {
            'coupon_id': coupon_id, 'coupon_balance': coupon_balance, 'expire_time': expire_time
        }
        message = notice + coupon_msg
        return self.build_body(hello_to=hello_to, message=message)

    def build_coupons_message(self, coupons):
        l_m = (self.TEMPLATE_COUPON_MESSAGE % {
                'coupon_id': cp.id, 'coupon_balance': cp.balance, 'expire_time': cp.expiration_time
            } for cp in coupons)

        return '\n'.join(l_m)

    def build_body(self, hello_to: str, message: str):
        return self.TEMPLATE_BODY % {'hello_to': hello_to, 'message': message}


class CouponQuerier:
    @staticmethod
    def get_expire_coupons(after_days: int, creation_time_gt: datetime = None, limit: int = 100):
        """
        查询指定天数后即将过期的资源券

        :param after_days: 指定天数后过期
        :param creation_time_gt: 创建时间大于此时间的券
        :param limit: 指定返回券数量
        """
        nt = timezone.now()
        expiration_time = nt + timedelta(days=after_days)
        lookups = {}
        if creation_time_gt:
            lookups['creation_time__gt'] = creation_time_gt

        qs = CashCoupon.objects.select_related('user', 'vo').filter(
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type__in=OwnerType.values,
            expiration_time__gt=nt,  # 未过期，排除已过期的
            expiration_time__lt=expiration_time,  # 将过期
            **lookups
        ).order_by('creation_time')

        return qs[:limit]

    @staticmethod
    def get_insufficient_coupons(threshold: Decimal, creation_time_gt: datetime = None, limit: int = 100):
        """
        查询余额不足指定金额的资源券

        :param threshold: 余额不足的阈值
        :param creation_time_gt: 创建时间大于此时间的券
        :param limit: 指定返回券数量
        """
        nt = timezone.now()
        lookups = {}
        if creation_time_gt:
            lookups['creation_time__gt'] = creation_time_gt

        qs = CashCoupon.objects.select_related('user', 'vo').filter(
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type__in=OwnerType.values,
            expiration_time__gt=nt,  # 未过期，排除已过期的
            balance__lt=threshold,
            **lookups
        ).order_by('creation_time')

        return qs[:limit]

    @staticmethod
    def get_expire_or_insufficient_queryset(
            threshold: Decimal, after_days: int, creation_time_gt: datetime = None):
        """
        查询指定天数后即将过期，或余额不足的资源券

        :param threshold: 余额不足的阈值
        :param after_days: 指定天数后过期
        :param creation_time_gt: 创建时间大于此时间的券
        """
        nt = timezone.now()
        expiration_time = nt + timedelta(days=after_days)
        lookups = {}
        if creation_time_gt:
            lookups['creation_time__gt'] = creation_time_gt

        qs = CashCoupon.objects.select_related('user', 'vo').filter(
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type__in=OwnerType.values,
            expiration_time__gt=nt,  # 未过期，排除已过期的
            **lookups
        ).filter(
            Q(expiration_time__lt=expiration_time, expire_notice_time__isnull=True
              ) | Q(balance__lt=threshold, balance_notice_time__isnull=True),  # 将过期 或者 余额不足
        ).order_by('creation_time')
        return qs

    def get_expire_or_insufficient_coupons(
            self, threshold: Decimal, after_days: int, creation_time_gt: datetime = None, limit: int = 100):
        """
        查询指定天数后即将过期，或余额不足的资源券

        :param threshold: 余额不足的阈值
        :param after_days: 指定天数后过期
        :param creation_time_gt: 创建时间大于此时间的券
        :param limit: 指定返回券数量
        """
        qs = self.get_expire_or_insufficient_queryset(
            threshold=threshold, after_days=after_days, creation_time_gt=creation_time_gt
        )
        return qs[:limit]

    def get_user_expire_or_insufficient_coupons(
            self, user_id: str, threshold: Decimal, after_days: int,
            creation_time_gt: datetime = None, limit: int = 100
    ):
        """
        查询用户的指定天数后即将过期，或余额不足的资源券

        :param user_id:
        :param threshold: 余额不足的阈值
        :param after_days: 指定天数后过期
        :param creation_time_gt: 创建时间大于此时间的券
        :param limit: 指定返回券数量
        """
        qs = self.get_expire_or_insufficient_queryset(
            threshold=threshold, after_days=after_days, creation_time_gt=creation_time_gt
        )
        qs = qs.filter(user_id=user_id, owner_type=OwnerType.USER.value)
        return qs[:limit]

    def get_vo_expire_or_insufficient_coupons(
            self, vo_id: str, threshold: Decimal, after_days: int,
            creation_time_gt: datetime = None, limit: int = 100
    ):
        """
        查询vo的指定天数后即将过期，或余额不足的资源券

        :param vo_id:
        :param threshold: 余额不足的阈值
        :param after_days: 指定天数后过期
        :param creation_time_gt: 创建时间大于此时间的券
        :param limit: 指定返回券数量
        """
        qs = self.get_expire_or_insufficient_queryset(
            threshold=threshold, after_days=after_days, creation_time_gt=creation_time_gt
        )
        qs = qs.filter(vo_id=vo_id, owner_type=OwnerType.VO.value)
        return qs[:limit]

    @staticmethod
    def get_vo_emails(vo: VirtualOrganization) -> list:
        vo_owner = vo.owner
        vo_admins = VoMember.objects.select_related(
            'user').filter(vo_id=vo.id, role=VoMember.Role.LEADER.value).all()
        receivers = [vo_owner.username]
        for m in vo_admins:
            receivers.append(m.user.username)

        return receivers

    @staticmethod
    def is_need_insufficient_notice(coupon: CashCoupon) -> bool:
        if coupon.status != CashCoupon.Status.AVAILABLE.value:
            return False

        if coupon.balance >= CouponNotifier.BALANCE_NOTICE_THRESHOLD:
            return False

        if coupon.balance_notice_time is None:
            return True

        return False

    @staticmethod
    def is_need_expire_notice(coupon: CashCoupon) -> bool:
        expiration_time = timezone.now() + timedelta(days=CouponNotifier.EXPIRE_NOTICE_BEFORE_DAYS)
        if coupon.expiration_time > expiration_time:
            return False

        if coupon.status != CashCoupon.Status.AVAILABLE.value:
            return False

        if coupon.expire_notice_time is None:
            return True

        return False

    @staticmethod
    def set_coupons_notice_time(
            coupon_ids: list, expire_notice_time: datetime = None, balance_notice_time: datetime = None
    ):
        update_fields = {}
        if expire_notice_time:
            update_fields['expire_notice_time'] = expire_notice_time

        if balance_notice_time:
            update_fields['balance_notice_time'] = balance_notice_time

        r = CashCoupon.objects.filter(id__in=coupon_ids).update(**update_fields)
        return r


class CouponSorter:
    def __init__(self, coupons: list):
        self.__coupons = coupons
        self.expire_coupons, self.insufficient_coupons, self.both_coupons = self.sort_coupons(coupons)

    def notice_coupons(self):
        return self.expire_coupons + self.insufficient_coupons + self.both_coupons

    def only_expire_coupon_ids(self):
        return [cp.id for cp in self.expire_coupons]

    def only_insufficient_coupon_ids(self):
        return [cp.id for cp in self.insufficient_coupons]

    def both_coupon_ids(self):
        """同时即将过期和余额不足"""
        return [cp.id for cp in self.both_coupons]

    def expire_coupon_ids(self):
        return self.only_expire_coupon_ids() + self.both_coupon_ids()

    def insufficient_coupon_ids(self):
        return self.only_insufficient_coupon_ids() + self.both_coupon_ids()

    @staticmethod
    def sort_coupons(coupons):
        expire_coupons = []
        insufficient_coupons = []
        both_coupons = []
        for cp in coupons:
            is_exp = CouponQuerier.is_need_expire_notice(coupon=cp)
            is_ins = CouponQuerier.is_need_insufficient_notice(coupon=cp)
            if is_exp and is_ins:
                both_coupons.append(cp)
            elif is_exp:
                expire_coupons.append(cp)
            elif is_ins:
                insufficient_coupons.append(cp)
            else:
                pass

        return expire_coupons, insufficient_coupons, both_coupons


class CouponNotifier:
    EXPIRE_NOTICE_BEFORE_DAYS = 7   # 不满多少天将过期才发通知
    BALANCE_NOTICE_THRESHOLD = Decimal('100')   # 券余额不足此阈值时通知

    templater = MessageTemplate()
    querier = CouponQuerier()

    def __init__(self, log_stdout: bool = False):
        self.logger = config_logger(name='coupon-logger', filename="coupon_notice.log", stdout=log_stdout)

    def run(self):
        self.loop_notice_together()
        # self.loop_expire()
        # self.loop_insufficient()

    def do_notice_together(self, sorter: CouponSorter, subject: str, message: str, receivers: list) -> bool:
        email = Email.send_email(
            subject=subject, message=message, receivers=receivers, tag=Email.Tag.COUPON.value
        )
        if email is None:
            return False

        nt = timezone.now()
        expire_ids = sorter.expire_coupon_ids()
        insu_ids = sorter.insufficient_coupon_ids()
        if expire_ids:
            r = self.querier.set_coupons_notice_time(coupon_ids=expire_ids, expire_notice_time=nt)

        if insu_ids:
            r = self.querier.set_coupons_notice_time(coupon_ids=insu_ids, balance_notice_time=nt)

        return True

    def notice_user_or_vo(self, coupons):
        ok = True
        target_done = []
        for cp in coupons:
            if cp.owner_type == OwnerType.USER.value:
                if cp.user_id not in target_done:
                    ok = self.notice_one_user(cp.user)
                    target_done.append(cp.user_id)
            elif cp.owner_type == OwnerType.VO.value:
                if cp.vo_id not in target_done:
                    ok = self.notice_one_vo(cp.vo)
                    target_done.append(cp.vo_id)
            else:
                pass

            if not ok:
                return False

        return True

    def notice_one_user(self, user):
        coupons = self.querier.get_user_expire_or_insufficient_coupons(
            user_id=user.id, threshold=self.BALANCE_NOTICE_THRESHOLD, after_days=self.EXPIRE_NOTICE_BEFORE_DAYS,
            limit=1000
        )
        if not coupons:
            return True

        sorter = CouponSorter(coupons=coupons)
        notice_coupons = sorter.notice_coupons()
        if not notice_coupons:
            return True

        receivers = [user.username]
        hello_to = user.username
        subject = self.templater.SUBJECT_EXPIRE_INSUFFICIENT
        coupons_msg = self.templater.build_coupons_message(notice_coupons)
        message = self.templater.build_body(
            hello_to=hello_to, message=self.templater.YOUR_EXPIRE_INSUFFICIENT_MESSAHE + '\n' + coupons_msg
        )
        ok = self.do_notice_together(sorter=sorter, subject=subject, message=message, receivers=receivers)
        if not ok:
            msg = f'过期或余额不足通知邮件发送失败，用户名{user.username}, {coupons_msg}'
            self.logger.warning(msg)
            return False

        return True

    def notice_one_vo(self, vo):
        coupons = self.querier.get_vo_expire_or_insufficient_coupons(
            vo_id=vo.id, threshold=self.BALANCE_NOTICE_THRESHOLD, after_days=self.EXPIRE_NOTICE_BEFORE_DAYS,
            limit=1000
        )
        if not coupons:
            return True

        sorter = CouponSorter(coupons=coupons)
        notice_coupons = sorter.notice_coupons()
        if not notice_coupons:
            return True

        receivers = self.querier.get_vo_emails(vo)
        subject = self.templater.SUBJECT_EXPIRE_INSUFFICIENT
        hello_to = f'项目组“{vo.name}”的成员'
        sorter = CouponSorter(coupons=coupons)
        coupons_msg = self.templater.build_coupons_message(notice_coupons)
        message = self.templater.build_body(
            hello_to=hello_to, message=self.templater.VO_EXPIRE_INSUFFICIENT_MESSAHE + '\n' + coupons_msg
        )
        ok = self.do_notice_together(sorter=sorter, subject=subject, message=message, receivers=receivers)
        if not ok:
            msg = f'过期或余额不足通知邮件发送失败，vo组名{vo.name}, {coupons_msg}'
            self.logger.warning(msg)
            return False

        return True

    def loop_notice_together(self):
        self.logger.warning('开始资源券通知。')
        creation_time_gt = None
        while True:
            try:
                coupons = self.querier.get_expire_or_insufficient_coupons(
                    threshold=self.BALANCE_NOTICE_THRESHOLD,
                    after_days=self.EXPIRE_NOTICE_BEFORE_DAYS, creation_time_gt=creation_time_gt, limit=100)
                len_cp = len(coupons)
                if len_cp == 0:
                    break

                creation_time_gt = coupons[0].creation_time  # 记录本次查询券的最小创建时间，发生错误时跳过此券
                ok = self.notice_user_or_vo(coupons=coupons)
                if not ok:
                    continue

                creation_time_gt = coupons[len_cp - 1].creation_time  # 未发生错误，记录本次查询券的最大创建时间
            except Exception as exc:
                msg = f'券过期或余额不足通知错误，{str(exc)}'
                self.logger.warning(msg)

        self.logger.warning('结束资源券通知。')

    def loop_expire(self):
        self.logger.warning('开始资源券过期通知。')
        creation_time_gt = None
        while True:
            try:
                coupons = self.querier.get_expire_coupons(
                    after_days=self.EXPIRE_NOTICE_BEFORE_DAYS, creation_time_gt=creation_time_gt, limit=100)
                if len(coupons) == 0:
                    break

                for coupon in coupons:
                    creation_time_gt = coupon.creation_time     # 记录当前券的创建时间，发生错误时跳过此券
                    ok = self.notice_expire_coupon(coupon)
                    if ok is False:
                        ok = self.notice_expire_coupon(coupon)

                    if ok is False:
                        msg = f'过期通知邮件发送失败，券编号 {coupon.id}, 余额 {coupon.balance} 点, ' \
                              f'过期时间 {coupon.expiration_time}。'
                        self.logger.warning(msg)
            except Exception as exc:
                msg = f'券过期通知错误，{str(exc)}'
                self.logger.warning(msg)

        self.logger.warning('结束资源券过期通知。')

    def loop_insufficient(self):
        self.logger.warning('开始资源券余额不足通知。')
        creation_time_gt = None
        while True:
            try:
                coupons = self.querier.get_insufficient_coupons(
                    threshold=self.BALANCE_NOTICE_THRESHOLD, creation_time_gt=creation_time_gt, limit=100)
                if len(coupons) == 0:
                    break

                for coupon in coupons:
                    creation_time_gt = coupon.creation_time     # 记录当前券的创建时间，发生错误时跳过此券
                    ok = self.notice_insufficient_coupon(coupon)
                    if ok is False:
                        ok = self.notice_insufficient_coupon(coupon)

                    if ok is False:
                        msg = f'余额不足通知邮件发送失败，券编号 {coupon.id}, 余额 {coupon.balance} 点, ' \
                              f'过期时间 {coupon.expiration_time}。'
                        self.logger.warning(msg)
            except Exception as exc:
                msg = f'券余额不足通知错误，{str(exc)}'
                self.logger.warning(msg)

        self.logger.warning('结束资源券余额不足通知。')

    def notice_expire_coupon(self, coupon: CashCoupon):
        """
        :return:
            True    # success
            False   # failed
            None    # no send email,
        """
        is_need = self.querier.is_need_expire_notice(coupon)
        if not is_need:
            return None

        if coupon.owner_type == OwnerType.VO.value:
            ok = self.notice_vo_expire(coupon)
        else:
            ok = self.notice_user_expire(coupon)

        return ok

    def notice_insufficient_coupon(self, coupon: CashCoupon):
        is_need = self.querier.is_need_insufficient_notice(coupon)
        if not is_need:
            return None

        if coupon.owner_type == OwnerType.VO.value:
            ok = self.notice_vo_insufficient(coupon)
        else:
            ok = self.notice_user_insufficient(coupon)

        return ok

    @staticmethod
    def do_notice(
            coupon: CashCoupon, subject: str, message: str, receivers: list,
            is_expire: bool = None, is_insufficient: bool = None
    ):
        """
        :return:
            True    # success
            False   # failed
        """
        email = Email.send_email(
            subject=subject, message=message, receivers=receivers, tag=Email.Tag.COUPON.value
        )
        if email is None:
            return False

        nt = timezone.now()
        update_fields = []
        if is_expire:
            coupon.expire_notice_time = nt
            update_fields.append('expire_notice_time')

        if is_insufficient:
            coupon.balance_notice_time = nt
            update_fields.append('balance_notice_time')

        coupon.save(update_fields=update_fields)
        return True

    def notice_user_expire(self, coupon: CashCoupon):
        """
        :return:
            True    # success
            False   # failed
            None    # no send email,
        """
        if not coupon.user:
            return None

        to_email = coupon.user.username
        hello_to = to_email
        receivers = [to_email]
        expire_time = str(coupon.expiration_time)
        subject = self.templater.SUBJECT_EXPIRE
        is_insufficient = False
        if self.querier.is_need_insufficient_notice(coupon):
            notice = self.templater.YOUR_EXPIRE_INSUFFICIENT_MESSAHE
            is_insufficient = True
        else:
            notice = self.templater.YOUR_EXPIRE_MESSAHE

        message = self.templater.build_notice_message(
            hello_to=hello_to, notice=notice,
            coupon_id=coupon.id, coupon_balance=str(coupon.balance), expire_time=expire_time
        )

        return self.do_notice(
            coupon=coupon, subject=subject, message=message, receivers=receivers,
            is_expire=True, is_insufficient=is_insufficient
        )

    def notice_vo_expire(self, coupon: CashCoupon):
        """
        :return:
            True    # success
            False   # failed
            None    # no send email,
        """
        vo = coupon.vo
        if not vo:
            return None

        receivers = self.querier.get_vo_emails(vo)
        subject = self.templater.SUBJECT_EXPIRE
        hello_to = f'项目组“{vo.name}”的成员'
        expire_time = str(coupon.expiration_time)
        is_insufficient = False
        if self.querier.is_need_insufficient_notice(coupon):
            notice = self.templater.VO_EXPIRE_INSUFFICIENT_MESSAHE
            is_insufficient = True
        else:
            notice = self.templater.VO_EXPIRE_MESSAHE

        message = self.templater.build_notice_message(
            hello_to=hello_to, notice=notice,
            coupon_id=coupon.id, coupon_balance=str(coupon.balance), expire_time=expire_time
        )

        return self.do_notice(
            coupon=coupon, subject=subject, message=message, receivers=receivers,
            is_expire=True, is_insufficient=is_insufficient
        )

    def notice_user_insufficient(self, coupon: CashCoupon):
        """
        :return:
            True    # success
            False   # failed
            None    # no send email,
        """
        if not coupon.user:
            return None

        to_email = coupon.user.username
        hello_to = to_email
        receivers = [to_email]
        expire_time = str(coupon.expiration_time)

        is_expire = False
        subject = self.templater.SUBJECT_INSUFFICIENT
        if self.querier.is_need_expire_notice(coupon):
            notice = self.templater.YOUR_EXPIRE_INSUFFICIENT_MESSAHE
            is_expire = True
        else:
            notice = self.templater.YOUR_INSUFFICIENT_MESSAHE

        message = self.templater.build_notice_message(
            hello_to=hello_to, notice=notice,
            coupon_id=coupon.id, coupon_balance=str(coupon.balance), expire_time=expire_time
        )

        return self.do_notice(
            coupon=coupon, subject=subject, message=message, receivers=receivers,
            is_expire=is_expire, is_insufficient=True
        )

    def notice_vo_insufficient(self, coupon: CashCoupon):
        """
        :return:
            True    # success
            False   # failed
            None    # no send email,
        """
        vo = coupon.vo
        if not vo:
            return None

        receivers = self.querier.get_vo_emails(vo)
        subject = self.templater.SUBJECT_INSUFFICIENT
        hello_to = f'项目组“{vo.name}”的成员'
        expire_time = str(coupon.expiration_time)
        is_expire = False
        if self.querier.is_need_expire_notice(coupon):
            notice = self.templater.YOUR_EXPIRE_INSUFFICIENT_MESSAHE
            is_expire = True
        else:
            notice = self.templater.YOUR_INSUFFICIENT_MESSAHE

        message = self.templater.build_notice_message(
            hello_to=hello_to, notice=notice,
            coupon_id=coupon.id, coupon_balance=str(coupon.balance), expire_time=expire_time
        )

        return self.do_notice(
            coupon=coupon, subject=subject, message=message, receivers=receivers,
            is_expire=is_expire, is_insufficient=True
        )
