import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum, Count

from apps.app_servers.models import Disk


class Command(BaseCommand):
    help = """
    manage.py diskstats --after="2023-12-01 00:00:00" --before="2024-01-01 00:00:00"
    """
    def add_arguments(self, parser):
        parser.add_argument(
            '--after', default=None, nargs='?', dest='after', const=None,
            help='The disks created after a specified time. 2023-06-01 00:00:00',
        )
        parser.add_argument(
            '--before', default=None, nargs='?', dest='before', const=None,
            help='The disks created before a specified time. 2023-06-30 00:00:00',
        )

    @staticmethod
    def str_to_time(time_str: str):
        try:
            t = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            return t.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return None

    def handle(self, *args, **options):
        after_str = options['after']
        before_str = options['before']
        if after_str is not None:
            after_time = self.str_to_time(after_str)
            if not after_time:
                raise CommandError(f'After time {after_time} is invalid.')
        else:
            after_time = None

        if before_str is not None:
            before_time = self.str_to_time(before_str)
            if not before_time:
                raise CommandError(f'Before time {before_time} is invalid.')
        else:
            before_time = None

        lookups = {}
        if after_time:
            lookups['creation_time__gte'] = after_time
        if before_time:
            lookups['creation_time__lte'] = before_time

        user_r = Disk.objects.filter(
            deleted=False, classification=Disk.Classification.PERSONAL.value, **lookups
        ).aggregate(
            total_size=Sum('size', default=0),
            total_disk_count=Count('id', distinct=True),
            total_user_count=Count('user_id', distinct=True)
        )
        vo_r = Disk.objects.filter(
            deleted=False, classification=Disk.Classification.VO.value, **lookups
        ).aggregate(
            total_size=Sum('size', default=0),
            total_disk_count=Count('id', distinct=True),
            total_vo_count=Count('vo_id', distinct=True)
        )
        deleted_r = Disk.objects.filter(
            deleted=True, **lookups
        ).aggregate(
            total_size=Sum('size', default=0),
            total_disk_count=Count('id', distinct=True),
        )
        s = f"""
        The time after {after_time} - before {before_time}

        [User]: 
            total size = {user_r['total_size']} GiB; 
            disk count = {user_r['total_disk_count']}; 
            user count = {user_r['total_user_count']}

        [VO]:
            total size = {vo_r['total_size']} GiB; 
            disk count = {vo_r['total_disk_count']}; 
            vo count = {vo_r['total_vo_count']}

        [Deleted Disk]:
            total size = {deleted_r['total_size']} GiB; 
            disk count = {deleted_r['total_disk_count']};
        """
        print(s)
