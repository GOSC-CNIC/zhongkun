from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand, CommandError


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
            private_key, public_key = self.generate_rsa_key(key_size=key_size)
        except Exception as exc:
            raise CommandError(f"Error, {str(exc)}.")

        self.stdout.write(self.style.SUCCESS(
            f"""[private_key]: \n{private_key}\n"""
            f"""[public_key]: \n{public_key}"""))

    @staticmethod
    def generate_rsa_key(key_size: int = 2048):
        pri_rsa = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        bytes_private_key = pri_rsa.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_key = bytes_private_key.decode('utf-8')

        public_rsa = pri_rsa.public_key()
        bytes_public_key = public_rsa.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key = bytes_public_key.decode('utf-8')

        return private_key, public_key
