from django.core.management.base import BaseCommand, CommandError
from storage.models import ObjectsService


class Command(BaseCommand):
    help = """
        python3 manage.py list_storage_service
    """

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        queryset = ObjectsService.objects.all()
        self.stdout.write(self.style.WARNING(f'Will list {queryset.count()} storage service.'))

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.list_service(services=queryset)

    def list_service(self, services):
        num = 1
        for s in services:
            self.stdout.write(self.style.SUCCESS(f'[{num}] Service id={s.id}, name={s.name}.'))
            num += 1
