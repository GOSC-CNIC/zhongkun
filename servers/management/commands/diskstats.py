from django.core.management.base import BaseCommand
from django.db.models import Sum, Count

from servers.models import Disk


class Command(BaseCommand):
    help = """
    manage.py diskstats"
    """

    def handle(self, *args, **options):
        user_r = Disk.objects.filter(
            deleted=False, classification=Disk.Classification.PERSONAL.value
        ).aggregate(
            total_size=Sum('size', default=0),
            total_disk_count=Count('id', distinct=True),
            total_user_count=Count('user_id', distinct=True)
        )
        vo_r = Disk.objects.filter(
            deleted=False, classification=Disk.Classification.VO.value
        ).aggregate(
            total_size=Sum('size', default=0),
            total_disk_count=Count('id', distinct=True),
            total_vo_count=Count('vo_id', distinct=True)
        )
        s = f"""
        [User]: 
            total size = {user_r['total_size']} GiB; 
            disk count = {user_r['total_disk_count']}; 
            user count = {user_r['total_user_count']}
        [VO]:
            total size = {vo_r['total_size']} GiB; 
            disk count = {vo_r['total_disk_count']}; 
            vo count = {vo_r['total_vo_count']}
        """
        print(s)
