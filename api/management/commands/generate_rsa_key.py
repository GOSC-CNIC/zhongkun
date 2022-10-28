from django.core.management.base import BaseCommand, CommandError

from utils.crypto.rsa import generate_rsa_key


class Command(BaseCommand):
    help = """
    python3 manage.py generat_rsa_key --keysize=2048
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--keysize', default=2048, dest='keysize', type=int,
            help="The size of key's bits",
        )

    def handle(self, *args, **options):
        key_size = options.get('keysize')

        self.stdout.write(self.style.WARNING(f'keysize={key_size}'))
        try:
            private_key, public_key = generate_rsa_key(key_size=key_size)
        except Exception as exc:
            raise CommandError(f"Error, {str(exc)}.")

        self.stdout.write(self.style.SUCCESS(
            f"""[private_key]: \n{private_key}\n"""
            f"""[public_key]: \n{public_key}"""))
