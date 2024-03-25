import os
import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework import serializers
from storage.models import ObjectsService, Bucket
from users.models import UserProfile
from bill.models import PayApp


class Command(BaseCommand):
    help = """
        manage.py update_app_public_key --filename="/home/pub.key" --app-id="xxx"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--filename', default=None, dest='filename', type=str,
            help='The file that import buckets from.',
        )
        parser.add_argument(
            '--app-id', default=None, dest='app_id', type=str,
            help='The app id.',
        )

    def handle(self, *args, **options):
        filename = options.get('filename')
        if not filename:
            filename = '/home/pub.key'
            self.stdout.write(self.style.WARNING(f'Not set filename, Try import key from file: {filename}'))
        else:
            self.stdout.write(self.style.WARNING(f'Import key from file: {filename}'))

        if not os.path.exists(filename):
            self.stdout.write(self.style.ERROR(
                f'File "{filename}" is not exists, Try param "--filename" to set filename'))
            return

        app_id = options.get('app_id')
        if not app_id:
            self.stdout.write(self.style.ERROR('Not set app_id id, Use param "--app-id" to set.'))
            raise CommandError("cancelled.")

        app = PayApp.objects.filter(id=app_id).first()
        if app is None:
            self.stdout.write(self.style.ERROR(f'APP is not exists, invalid app-id "{app_id}".'))
            raise CommandError("cancelled.")

        self.stdout.write(self.style.WARNING(f'Will import to APP: {app.name}.'))

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.update_buckets(filename=filename, app=app)

    def update_buckets(self, filename: str, app: PayApp):
        with open(filename, 'r') as f:
            key = f.read()
            print(f'old key: \n{app.rsa_public_key}')
            print(f'new key: \n{key}')
            app.rsa_public_key = key
            app.save(update_fields=['rsa_public_key'])

        self.stdout.write(self.style.SUCCESS(f'Successfully update app: {app.name}.'))
