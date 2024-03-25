import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum, Count

from servers.models import Server, ServerArchive


class Command(BaseCommand):
    help = """
    manage.py serverstats"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--after', default=None, nargs='?', dest='after', const=None,
            help='The servers created after a specified time. 2023-06-01 00:00:00',
        )
        parser.add_argument(
            '--before', default=None, nargs='?', dest='before', const=None,
            help='The servers created before a specified time. 2023-06-30 00:00:00',
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

        server_r = Server.objects.filter(
            task_status=Server.TASK_CREATED_OK, **lookups
        ).aggregate(
            total_ram_size=Sum('ram', default=0),
            total_cpu_size=Sum('vcpus', default=0),
            total_server_count=Count('id', distinct=True),
        )
        archive_r = ServerArchive.objects.filter(
            task_status=Server.TASK_CREATED_OK, archive_type=ServerArchive.ArchiveType.ARCHIVE.value, **lookups
        ).aggregate(
            total_ram_size=Sum('ram', default=0),
            total_cpu_size=Sum('vcpus', default=0),
            total_server_count=Count('id', distinct=True),
        )
        s = f"""
        The time after {after_time} - before {before_time}
        [Server]: 
            total ram = {server_r['total_ram_size']} GiB; 
            total cpu = {server_r['total_cpu_size']}; 
            total count = {server_r['total_server_count']}
        [Archive Server]:
            total ram = {archive_r['total_ram_size']} GiB; 
            total cpu = {archive_r['total_cpu_size']}; 
            total count = {archive_r['total_server_count']}
        """
        print(s)
