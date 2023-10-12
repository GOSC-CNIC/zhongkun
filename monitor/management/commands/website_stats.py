from django.core.management.base import BaseCommand
from django.db.models import Count

from monitor.models import MonitorWebsite


class Command(BaseCommand):
    help = """
    manage.py website_stats"
    """

    def handle(self, *args, **options):
        r = MonitorWebsite.objects.aggregate(
            total_count=Count('id'),
            total_task_count=Count('url_hash', distinct=True),
            total_user_count=Count('user_id', distinct=True)
        )

        s = f"""
            total user task count = {r['total_count']}; 
            total task count = {r['total_task_count']}; 
            total user count = {r['total_user_count']}
        """
        print(s)
