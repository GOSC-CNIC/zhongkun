from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as dj_timezone

from apps.users.models import Email, UserProfile
from apps.servers.models import Server
from apps.app_vo.models import VoMember
from apps.app_wallet.models import CashCoupon, OwnerType


# 邮件标题
SUBJECT = '【升级通知】中国科技云一体化云服务平台系统升级维护'
# 邮件内容
EMAIL_CONTENT = """
尊敬的用户，您好：

    拟定于2024年9月13日（周五）17:00至19:00对中国科技云一体化云服务平台（https://service.cstcloud.cn） 进行系统升级，
    升级期间前端页面暂不能访问，云主机和对象存储访问不受影响。在此期间给您带来的不便敬请谅解。

祝好
"""


class Command(BaseCommand):
    help = 'Send email to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all-users', nargs='?', dest='all_users', const=True,
            help='email to all users')
        parser.add_argument(
            '--res-users', nargs='?', dest='resource_users', const=True,
            help='users that have server')
        parser.add_argument(
            '--active-months', nargs='?', dest='active_months', type=int,
            help='users that last active in months')
        parser.add_argument(
            '--username', nargs='?', dest='username', type=str,
            help='send email to username')

    def handle(self, *args, **options):
        resource_users = options['resource_users']
        active_months = options['active_months']
        all_users = options['all_users']
        username = options['username']

        if len(SUBJECT) < 5:
            self.stdout.write(self.style.NOTICE('No set email subject.'))
            return

        if len(EMAIL_CONTENT) < 20:
            self.stdout.write(self.style.NOTICE('No set email content.'))
            return

        if username:
            u = UserProfile.objects.filter(username=username).first()
            if u is None:
                self.stdout.write(self.style.NOTICE(f'Not found user "{username}".'))
                return

            users = [u]
            self.stdout.write(self.style.NOTICE(f'Will send email to "{username}".'))

        elif resource_users:
            users = self.get_has_resource_users()
            self.stdout.write(self.style.NOTICE(f'Will send email to {len(users)} user that have resources.'))
        elif active_months:
            users = self.get_last_active_users(months=active_months)
            self.stdout.write(self.style.NOTICE(
                f'Will send email to {len(users)} user that last active in {active_months} months.'))
        elif all_users:
            users = self.get_all_users()
            self.stdout.write(self.style.NOTICE(f'Will send email to all {len(users)} users.'))
        else:
            self.stdout.write(self.style.NOTICE('Please select users to email.'))
            return

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.send_email_users_each(users)
        # self.send_email_users_by_len(users)

    @staticmethod
    def chunks(values: list, per_num: int = 5):
        ret = []
        for val in values:
            ret.append(val)
            if len(ret) >= per_num:
                yield ret
                ret = []

        if ret:
            yield ret

    @staticmethod
    def chunk_email_len(values: list, per_max_len: int = 253):
        receivers = []
        receiver_str = ''
        for val in values:
            un = val.username
            if receiver_str:
                receiver_str += f';{un}'
            else:
                receiver_str = un

            if len(receiver_str) > per_max_len:
                yield receivers
                receivers = [un]
                receiver_str = un
            else:
                receivers.append(un)

        if receivers:
            yield receivers

    def send_email_users_by_len(self, users):
        count = 0
        for receivers in self.chunk_email_len(users, per_max_len=253):
            try:
                Email.send_email(
                    subject=SUBJECT, receivers=receivers, message=EMAIL_CONTENT, tag=Email.Tag.OPS.value)
            except Exception as exc:
                self.stdout.write(self.style.NOTICE(f'Error send email({receivers}), {str(exc)}'))

            count += 1

        self.stdout.write(self.style.SUCCESS(f'OK send {count} emails.'))

    def send_email_users_each(self, users):
        count = 0
        for user in users:
            username = user.username
            try:
                Email.send_email(
                    subject=SUBJECT, receivers=[username], message=EMAIL_CONTENT, tag=Email.Tag.OPS.value)
            except Exception as exc:
                self.stdout.write(self.style.NOTICE(f'Error send email({username}), {str(exc)}'))

            count += 1
            self.stdout.write(self.style.SUCCESS(f'OK send to {username}.'))

        self.stdout.write(self.style.SUCCESS(f'OK send {count} emails.'))

    @staticmethod
    def get_last_active_users(months: int):
        nt = dj_timezone.now()
        active_time = nt + timedelta(days=30*months)
        users = UserProfile.objects.filter(is_active=True, last_active__gt=active_time).order_by('date_joined')
        return users

    @staticmethod
    def get_all_users():
        return UserProfile.objects.filter(is_active=True).order_by('date_joined')

    @staticmethod
    def get_has_resource_users():
        user_map = {}
        servers = Server.objects.select_related('user').filter(classification=Server.Classification.PERSONAL.value)
        for s in servers:
            u = s.user
            user_map[u.id] = u

        vo_ids = Server.objects.filter(classification=Server.Classification.VO.value).values_list('vo_id', flat=True)
        vo_ids = list(set(vo_ids))
        members = VoMember.objects.select_related('user').filter(vo_id__in=vo_ids)
        for m in members:
            u = m.user
            user_map[u.id] = u

        cc_qs = CashCoupon.objects.select_related('user').filter(
            status=CashCoupon.Status.AVAILABLE.value, balance__gt=Decimal('0'), owner_type=OwnerType.USER.value)
        for cc in cc_qs:
            u = cc.user
            user_map[u.id] = u

        users = list(user_map.values())
        users.sort(key=lambda x: x.date_joined, reverse=False)

        return users
