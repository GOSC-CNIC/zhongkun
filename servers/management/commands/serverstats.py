from django.core.management.base import BaseCommand
from django.db.models import Sum, Count

from servers.models import Server, ServerArchive


class Command(BaseCommand):
    help = """
    manage.py serverstats"
    """

    def handle(self, *args, **options):
        server_r = Server.objects.filter(
            task_status=Server.TASK_CREATED_OK
        ).aggregate(
            total_ram_size=Sum('ram', default=0),
            total_cpu_size=Sum('vcpus', default=0),
            total_server_count=Count('id', distinct=True),
        )
        archive_r = ServerArchive.objects.filter(
            task_status=Server.TASK_CREATED_OK, archive_type=ServerArchive.ArchiveType.ARCHIVE.value
        ).aggregate(
            total_ram_size=Sum('ram', default=0),
            total_cpu_size=Sum('vcpus', default=0),
            total_server_count=Count('id', distinct=True),
        )
        s = f"""
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
