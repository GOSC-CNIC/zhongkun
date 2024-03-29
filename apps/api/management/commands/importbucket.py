import os
import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework import serializers
from storage.models import ObjectsService, Bucket
from users.models import UserProfile


class Command(BaseCommand):
    help = """
        import buckets from file '/home/export-bucket.txt':
        manage.py importbucket --filename="/home/export-bucket.txt" --serviceid="xxx"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--filename', default=None, dest='filename', type=str,
            help='The file that import buckets from.',
        )
        parser.add_argument(
            '--serviceid', default=None, dest='service_id', type=str,
            help='The service that bucket belong to.',
        )

    def handle(self, *args, **options):
        filename = options.get('filename')
        if not filename:
            filename = '/home/export-bucket.txt'
            self.stdout.write(self.style.WARNING(f'Not set filename, Try import bucket from file: {filename}'))
        else:
            self.stdout.write(self.style.WARNING(f'Import bucket from file: {filename}'))

        if not os.path.exists(filename):
            self.stdout.write(self.style.ERROR(
                f'File "{filename}" is not exists, Try param "--filename" to set filename'))
            return

        service_id = options.get('service_id')
        if not service_id:
            self.stdout.write(self.style.ERROR('Not set service id, Use param "--serviceid" to set.'))
            raise CommandError("cancelled.")

        service = ObjectsService.objects.filter(id=service_id).first()
        if service is None:
            self.stdout.write(self.style.ERROR(f'Service is not exists, invalid serviceid "{service_id}".'))
            raise CommandError("cancelled.")

        self.stdout.write(self.style.WARNING(f'Will import to service: {service.name}.'))

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.import_buckets(filename=filename, service=service)

    def import_buckets(self, filename: str, service):
        bucket_count = 0
        import_count = 0
        with open(filename, 'r') as f:
            while True:
                line = f.readline()
                if not line:
                    break

                bucket_count += 1
                b = json.loads(s=line)
                bucket = self.import_one_bucket(b=b, service=service)
                if bucket is not None:
                    import_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully import {import_count} / {bucket_count} buckets.'))

    def import_one_bucket(self, b: dict, service):
        """
        :return:
            bucket: import ok
            None: not import
        """
        data = self.validate_bucket_data(b)
        bucket_id = data['bucket_id']
        bucket_name = data['bucket_name']
        creation_time = data['creation_time']
        username = data['username']

        if self.is_bucket_already_exists(service_id=service.id, bucket_name=bucket_name):
            self.stdout.write(self.style.WARNING(
                f'bucket(id={bucket_id}, name={bucket_name}) already exists, Skip it.'))
            return None

        if username:
            user = UserProfile.objects.filter(username=username).first()
        else:
            user = None

        if user is None:
            self.stdout.write(self.style.WARNING(
                f'bucket(id={bucket_id}, name={bucket_name}), user({username}) not exists, Skip it.'))
            return None

        b = self.create_bucket(
            service_id=service.id,
            bucket_id=bucket_id,
            bucket_name=bucket_name,
            creation_time=creation_time,
            user_id=user.id
        )

        return b

    @staticmethod
    def is_bucket_already_exists(service_id: str, bucket_name: str):
        return Bucket.objects.filter(service_id=service_id, name=bucket_name).exists()

    def validate_bucket_data(self, b: dict):
        bucket_id = b['id']
        bucket_name = b['name']
        try:
            creation_time = serializers.DateTimeField().to_internal_value(b['created_time'])
        except Exception as exc:
            self.stdout.write(self.style.WARNING(
                f'bucket(id={bucket_id}, name={bucket_name}) creation_time is None, Set now.'))

            creation_time = timezone.now()

        if creation_time is None:
            creation_time = timezone.now()

        if b['user']:
            username = b['user']['username']
        else:
            username = None

        return {
            'bucket_id': bucket_id,
            'bucket_name': bucket_name,
            'creation_time': creation_time,
            'username': username                        # None
        }

    @staticmethod
    def create_bucket(service_id: str, bucket_id: str, bucket_name: str, creation_time, user_id: str):
        bucket = Bucket(
            name=bucket_name, bucket_id=bucket_id, user_id=user_id,
            service_id=service_id, creation_time=creation_time
        )
        bucket.save(force_insert=True)
        return bucket
