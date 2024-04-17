from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.monitor.models import MonitorWebsite, MonitorWebsiteTask


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
        task_count = MonitorWebsiteTask.objects.count()

        s = f"""
            total user task count = {r['total_count']}; 
            total task count = {r['total_task_count']}; 
            total user count = {r['total_user_count']};

            task table count = {task_count}; 
        """
        print(s)
