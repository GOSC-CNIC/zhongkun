from decimal import Decimal
import time

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.app_wallet.models import UserPointAccount, VoPointAccount, Recharge
from apps.app_wallet.managers.recharge import RechargeManager
from utils.model import OwnerType


class Command(BaseCommand):
    help = """
    余额欠费充值清零
    manage.py balance_due_zero
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--user', default='', dest='user', type=str,
            help='The user whose balance will be cleared to zero.',
        )
        parser.add_argument(
            '--vo-id', default='', dest='vo_id', type=str,
            help='The vo whose balance will be cleared to zero.',
        )
        parser.add_argument(
            '--all-user', dest='all_user', type=bool, nargs='?', default=False, const=True,
            help='All user whose balance will be cleared to zero.',
        )
        parser.add_argument(
            '--all-vo', dest='all_vo', type=str, nargs='?', default=False, const=True,
            help='All vo whose balance will be cleared to zero.',
        )

    def handle(self, *args, **options):
        username = options['user']
        if username:
            self.stdout.write(self.style.ERROR(f'Will clearing user "{username}" balance arrears?'))
            if input('Are you sure you want to do this?\n' + "Type 'yes' to continue, or 'no' to cancel: ") == 'yes':
                self.do_zero_balance_for_user(username=username)
        elif options['all_user']:
            self.stdout.write(self.style.ERROR(f'Will clearing all "user" balance arrears?'))
            if input('Are you sure you want to do this?\n' + "Type 'yes' to continue, or 'no' to cancel: ") == 'yes':
                self.do_zero_user_balance()

        vo_id = options['vo_id']
        if vo_id:
            self.do_zero_balance_for_vo(vo_id=vo_id)
        elif options['all_vo']:
            self.stdout.write('\n\n')
            self.stdout.write(self.style.ERROR(f'Will clearing all "vo" balance arrears?'))
            if input('Are you sure you want to do this?\n' + "Type 'yes' to continue, or 'no' to cancel: ") == 'yes':
                self.do_zero_vo_balance()

    def do_zero_user_balance(self):
        self.stdout.write(self.style.WARNING(f"Start 清零余额欠费的用户账户"))
        ok_count = 0
        failed_count = 0
        last_creation_time = None
        while True:
            try:
                accounts = self.get_user_balance_account(creation_time_gt=last_creation_time, limit=100)
                if len(accounts) == 0:
                    break

                for ac in accounts:
                    if ac.balance < Decimal('0'):
                        try:
                            user = ac.user
                            self.do_recharge(
                                owner_type=OwnerType.USER.value, owner_id=user.id, owner_name=user.username,
                                amount=-ac.balance
                            )
                        except Exception as exc:
                            last_creation_time = ac.creation_time
                            failed_count += 1
                            self.stdout.write(self.style.ERROR(f"清零用户“{ac.user.username}”余额错误，{str(exc)}"))
                            continue

                        ok_count += 1

                    last_creation_time = ac.creation_time
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"{str(exc)}"))
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS(f"End 清零余额欠费的用户账户，成功：{ok_count}，失败：{failed_count}"))

    def do_zero_balance_for_user(self, username: str):
        ac = UserPointAccount.objects.select_related('user').filter(user__username=username).first()
        if not ac:
            self.stdout.write(self.style.WARNING(f"End 指定的清零余额欠费的用户“{username}”账户不存在"))
            return

        if ac.balance < Decimal('0'):
            try:
                user = ac.user
                self.do_recharge(
                    owner_type=OwnerType.USER.value, owner_id=user.id, owner_name=user.username,
                    amount=-ac.balance
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"清零用户“{ac.user.username}”余额错误，{str(exc)}"))

            self.stdout.write(self.style.SUCCESS(f"End 清零余额欠费的用户“{ac.user.username}”账户，成功"))
        else:
            self.stdout.write(self.style.SUCCESS(f"End 用户“{ac.user.username}”余额账户未欠费。"))

    def do_zero_vo_balance(self):
        self.stdout.write(self.style.WARNING(f"Start 清零余额欠费的VO账户"))
        ok_count = 0
        failed_count = 0
        last_creation_time = None
        while True:
            try:
                accounts = self.get_vo_balance_account(creation_time_gt=last_creation_time, limit=1)
                if len(accounts) == 0:
                    break

                for ac in accounts:
                    if ac.balance < Decimal('0'):
                        try:
                            vo = ac.vo
                            self.do_recharge(
                                owner_type=OwnerType.VO.value, owner_id=vo.id, owner_name=vo.name,
                                amount=-ac.balance
                            )
                        except Exception as exc:
                            last_creation_time = ac.creation_time
                            failed_count += 1
                            self.stdout.write(self.style.ERROR(f"清零vo组“{ac.vo.name}”余额错误，{str(exc)}"))
                            continue

                        ok_count += 1

                    last_creation_time = ac.creation_time
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"{str(exc)}"))
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS(f"End 清零余额欠费的VO账户，成功：{ok_count}，失败：{failed_count}"))

    def do_zero_balance_for_vo(self, vo_id: str):
        ac = VoPointAccount.objects.select_related('vo').filter(vo_id=vo_id).first()
        if not ac:
            self.stdout.write(self.style.WARNING(f"End 指定的清零余额欠费的vo id“{vo_id}”账户不存在"))
            return

        vo = ac.vo
        self.stdout.write(self.style.ERROR(f'Will clearing VO "{vo.name}" balance arrears?'))
        if input('Are you sure you want to do this?\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            return

        if ac.balance < Decimal('0'):
            try:
                self.do_recharge(
                    owner_type=OwnerType.VO.value, owner_id=vo.id, owner_name=vo.name,
                    amount=-ac.balance
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"清零VO“{vo.name}”余额错误，{str(exc)}"))

            self.stdout.write(self.style.SUCCESS(f"End 清零余额欠费的VO“{vo.name}”账户，成功"))
        else:
            self.stdout.write(self.style.SUCCESS(f"End VO “{vo.name}”余额账户未欠费。"))

    @staticmethod
    def get_user_balance_account(creation_time_gt, limit: int):
        qs = UserPointAccount.objects.select_related('user').filter(balance__lt=Decimal('0')).order_by('creation_time')
        if creation_time_gt:
            qs = qs.filter(creation_time__gt=creation_time_gt)

        return qs[0:limit]

    @staticmethod
    def get_vo_balance_account(creation_time_gt, limit: int):
        qs = VoPointAccount.objects.select_related('vo').filter(balance__lt=Decimal('0')).order_by('creation_time')
        if creation_time_gt:
            qs = qs.filter(creation_time__gt=creation_time_gt)

        return qs[0:limit]

    @staticmethod
    def do_recharge(owner_type: str, owner_id: str, owner_name: str, amount: Decimal):
        nt = timezone.now()
        with transaction.atomic():
            recharge = RechargeManager.create_wait_recharge(
                trade_channel=Recharge.TradeChannel.MANUAL.value, total_amount=amount,
                owner_type=owner_type, owner_id=owner_id, owner_name=owner_name,
                remark='欠费清零', creation_time=nt, executor='脚本'
            )
            RechargeManager.set_recharge_pay_success(
                recharge=recharge, out_trade_no='', channel_account='',
                channel_fee=Decimal('0'), receipt_amount=Decimal('0'), success_time=nt
            )
            RechargeManager().do_recharge_to_balance(recharge_id=recharge.id)
