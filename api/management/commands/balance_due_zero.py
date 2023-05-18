from decimal import Decimal
import time

from django.core.management.base import BaseCommand

from bill.models import UserPointAccount, VoPointAccount


class Command(BaseCommand):
    help = """
    余额欠费清零
    manage.py balance_due_zero
    """

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self.stdout.write(self.style.ERROR(f'Will clearing "user" balance arrears?'))
        if input('Are you sure you want to do this?\n' + "Type 'yes' to continue, or 'no' to cancel: ") == 'yes':
            self.do_zero_user_balance()

        self.stdout.write('\n\n')
        self.stdout.write(self.style.ERROR(f'Will clearing "vo" balance arrears?'))
        if input('Are you sure you want to do this?\n' + "Type 'yes' to continue, or 'no' to cancel: ") == 'yes':
            self.do_zero_vo_balance()

    def do_zero_user_balance(self):
        self.stdout.write(self.style.WARNING(f"Start 清零余额欠费的用户账户"))
        ok_count = 0
        failed_count = 0
        last_creation_time = None
        while True:
            try:
                accounts = self.get_user_balance_account(creation_time_gt=last_creation_time, limit=1)
                if len(accounts) == 0:
                    break

                for ac in accounts:
                    if ac.balance < Decimal('0'):
                        ac.balance = Decimal('0')
                        try:
                            ac.save(update_fields=['balance'])
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
                        ac.balance = Decimal('0')
                        try:
                            ac.save(update_fields=['balance'])
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

    @staticmethod
    def get_user_balance_account(creation_time_gt, limit: int):
        qs = UserPointAccount.objects.filter(balance__lt=Decimal('0')).order_by('creation_time')
        if creation_time_gt:
            qs = qs.filter(creation_time__gt=creation_time_gt)

        return qs[0:limit]

    @staticmethod
    def get_vo_balance_account(creation_time_gt, limit: int):
        qs = VoPointAccount.objects.filter(balance__lt=Decimal('0')).order_by('creation_time')
        if creation_time_gt:
            qs = qs.filter(creation_time__gt=creation_time_gt)

        return qs[0:limit]
