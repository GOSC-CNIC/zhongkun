import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from django.utils import timezone

from servers.models import Server, ServerArchive


class Command(BaseCommand):
    help = """
    manage.py servertime --server-starttime --all"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--server-starttime', default=None, nargs='?', dest='server-starttime', const=True,
            help='update server start_time == create_time.',
        )

        parser.add_argument(
            '--archive-starttime-rand', default=None, nargs='?', dest='archive-starttime-rand', const=True,
            help='Update the value of archive start_time so that it is a few days ahead of the delete_time.',
        )

        parser.add_argument(
            '--all', default=None, nargs='?', dest='all', const=True,
            help='all server or archive.',
        )

        parser.add_argument(
            # 当命令行有此参数时取值const, 否则取值default
            '--test', default=None, nargs='?', dest='test', const=True,
            help='test.',
        )

    def handle(self, *args, **options):
        is_all = options['all']
        if not is_all:
            raise CommandError(f"use param all.")

        server_starttime = options.get('server-starttime', None)
        if server_starttime:
            self.update_server_start_time()
            return

        archive_start_time_rand = options.get('archive-starttime-rand', None)
        if archive_start_time_rand:
            self.archive_start_time_rand()
            return

        raise CommandError("Nothing to do.")

    def update_server_start_time(self):
        count = Server.objects.exclude(start_time=F('creation_time')).count()
        self.stdout.write(self.style.NOTICE(f"Server count: {count}, update start_time to it's creation_time"))
        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action buckets cancelled.")

        rows = Server.objects.exclude(start_time=F('creation_time')).update(start_time=F('creation_time'))
        self.stdout.write(self.style.SUCCESS(f"OK, update {rows} Server start_time to it's creation_time"))

    def archive_start_time_rand(self):
        last_deleted_time = timezone.now()
        count = ServerArchive.objects.filter(deleted_time__lte=last_deleted_time).count()
        self.stdout.write(self.style.NOTICE(f"Server count: {count}, update start_time to it's creation_time"))
        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action buckets cancelled.")

        error_times = 0
        while True:
            try:
                qs = ServerArchive.objects.filter(deleted_time__lte=last_deleted_time).order_by('-deleted_time')
                archives = qs[0:100]
                count = len(archives)
                for archive in archives:
                    archive.start_time = archive.deleted_time - timedelta(days=random.randint(1, 365))
                    archive.save(update_fields=['start_time'])
                    last_deleted_time = archive.deleted_time

                self.stdout.write(self.style.SUCCESS(f"OK, update {count} Archive start_time"))
                if count < 100:     # 完了
                    break

                error_times = 0
            except Exception as e:
                error_times += 1
                if error_times > 3:
                    self.stdout.write(self.style.ERROR(f"Cancelled, too many error times"))
                    break

                self.stdout.write(self.style.ERROR(f"ERROR, update Archive start_time， {str(e)}"))
