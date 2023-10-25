from django.core.management.base import BaseCommand
from django.db.models import Sum, Count

from storage.models import Bucket, BucketArchive


class Command(BaseCommand):
    help = """
    manage.py bucketstats"
    """

    def handle(self, *args, **options):
        bucket_r = Bucket.objects.filter(
        ).aggregate(
            total_storage_size=Sum('storage_size', default=0),
            total_object_count=Sum('object_count', default=0),
            total_bucket_count=Count('id', distinct=True),
        )
        archive_r = BucketArchive.objects.filter(
        ).aggregate(
            total_storage_size=Sum('storage_size', default=0),
            total_object_count=Sum('object_count', default=0),
            total_bucket_count=Count('id', distinct=True),
        )
        s = f"""
        [Bucket]: 
            total storage size = {bucket_r['total_storage_size'] / 1024**3} GiB; 
            total object count = {bucket_r['total_object_count']}; 
            total bucket count = {bucket_r['total_bucket_count']}
        [Archive Bucket]:
            total storage size = {archive_r['total_storage_size'] / 1024**3} GiB; 
            total object count = {archive_r['total_object_count']}; 
            total bucket count = {archive_r['total_bucket_count']}
        """
        print(s)
