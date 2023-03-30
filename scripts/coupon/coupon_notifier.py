import logging
import sys
from decimal import Decimal
from datetime import timedelta, datetime
from pathlib import Path

from django.utils import timezone

from bill.models import CashCoupon
from users.models import Email
from vo.models import VirtualOrganization, VoMember
from utils.model import OwnerType


def config_logger(name: str = 'coupon-logger', level=logging.INFO, stdout: bool = False):
    log_dir = Path('/var/log/nginx')
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s ",  # 配置输出日志格式
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    if stdout:
        std_handler = logging.StreamHandler(stream=sys.stdout)
        std_handler.setFormatter(formatter)
        logger.addHandler(std_handler)

    file_handler = logging.FileHandler(filename=log_dir.joinpath("coupon_notice.log"))
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.WARNING)
    logger.addHandler(file_handler)
    return logger


class MessageTemplate:
    TEMPLATE_BODY = """
    你好，%(hello_to)s:

    %(message)s

    谢谢
    中国科技云一体化云服务平台(https://service.cstcloud.cn)
    """

    SUBJECT_EXPIRE = '代金券过期通知'
    SUBJECT_INSUFFICIENT = '代金券余额不足通知'
    YOUR_EXPIRE_MESSAHE = "你的代金券即将过期。"
    YOUR_INSUFFICIENT_MESSAHE = "你的代金券余额不足。"
    YOUR_EXPIRE_INSUFFICIENT_MESSAHE = "你的代金券即将过期，代金券余额不足。"
    VO_EXPIRE_MESSAHE = "项目组的代金券即将过期。"
    VO_INSUFFICIENT_MESSAHE = "项目组的代金券余额不足。"
    VO_EXPIRE_INSUFFICIENT_MESSAHE = "项目组的代金券即将过期，代金券余额不足。"
    TEMPLATE_COUPON_MESSAGE = "代金券编号为 %(coupon_id)s ，余额为 %(coupon_balance)s 点，过期时间为 %(expire_time)s。"

    def build_notice_message(self, hello_to: str, notice: str, coupon_id: str, coupon_balance: str, expire_time: str):
        coupon_msg = self.TEMPLATE_COUPON_MESSAGE % {
            'coupon_id': coupon_id, 'coupon_balance': coupon_balance, 'expire_time': expire_time
        }
        message = notice + coupon_msg
        return self.TEMPLATE_BODY % {'hello_to': hello_to, 'message': message}


class CouponNotifier:
    EXPIRE_NOTICE_BEFORE_DAYS = 7   # 不满多少天将过期才发通知
    BALANCE_NOTICE_THRESHOLD = Decimal('100')   # 券余额不足此阈值时通知

    templater = MessageTemplate()
    logger = config_logger()

    def __init__(self):
        pass

    def run(self):
        self.loop_expire()
        self.loop_insufficient()

    def loop_expire(self):
        self.logger.warning('开始代金券过期通知。')
        creation_time_gt = None
        while True:
            try:
                coupons = self.get_expire_coupons(
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

        self.logger.warning('结束代金券过期通知。')

    def loop_insufficient(self):
        self.logger.warning('开始代金券余额不足通知。')
        creation_time_gt = None
        while True:
            try:
                coupons = self.get_insufficient_coupons(
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

        self.logger.warning('结束代金券余额不足通知。')

    @staticmethod
    def get_expire_coupons(after_days: int, creation_time_gt: datetime = None, limit: int = 100):
        """
        查询指定天数后即将过期的代金券

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
            expiration_time__gt=nt,     # 未过期，排除已过期的
            expiration_time__lt=expiration_time,     # 将过期
            **lookups
        ).order_by('creation_time')

        return qs[:limit]

    @staticmethod
    def get_insufficient_coupons(threshold: Decimal, creation_time_gt: datetime = None, limit: int = 100):
        """
        查询余额不足指定金额的代金券

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

    def notice_expire_coupon(self, coupon: CashCoupon):
        """
        :return:
            True    # success
            False   # failed
            None    # no send email,
        """
        is_need = self.is_need_expire_notice(coupon)
        if not is_need:
            return None

        if coupon.owner_type == OwnerType.VO.value:
            ok = self.notice_vo_expire(coupon)
        else:
            ok = self.notice_user_expire(coupon)

        return ok

    def notice_insufficient_coupon(self, coupon: CashCoupon):
        is_need = self.is_need_insufficient_notice(coupon)
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
            subject=subject, message=message, receivers=receivers
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
        if self.is_need_insufficient_notice(coupon):
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

        receivers = self._get_vo_emails(vo)
        subject = self.templater.SUBJECT_EXPIRE
        hello_to = f'项目组“{vo.name}”的成员'
        expire_time = str(coupon.expiration_time)
        is_insufficient = False
        if self.is_need_insufficient_notice(coupon):
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
        if self.is_need_expire_notice(coupon):
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

        receivers = self._get_vo_emails(vo)
        subject = self.templater.SUBJECT_INSUFFICIENT
        hello_to = f'项目组“{vo.name}”的成员'
        expire_time = str(coupon.expiration_time)
        is_expire = False
        if self.is_need_expire_notice(coupon):
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

    @staticmethod
    def _get_vo_emails(vo: VirtualOrganization) -> list:
        vo_owner = vo.owner
        vo_admins = VoMember.objects.select_related(
            'user').filter(vo_id=vo.id, role=VoMember.Role.LEADER.value).all()
        receivers = [vo_owner.username]
        for m in vo_admins:
            receivers.append(m.user.username)

        return receivers
