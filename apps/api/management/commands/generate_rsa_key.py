from pathlib import Path

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
        parser.add_argument(
            '--save-to', default=None, dest='save-to', type=str,
            help='The dir that import key files to.',
        )

    def handle(self, *args, **options):
        key_size = options.get('keysize')
        save_to = options.get('save-to')
        if not save_to:
            save_to = '/home'
            self.stdout.write(self.style.WARNING(f'Not set "save-to", Try save key file to: {save_to}'))
        else:
            self.stdout.write(self.style.WARNING(f'Try save key file to: {save_to}'))

        path_dir = Path(save_to)
        if not path_dir.is_dir():
            self.stdout.write(self.style.ERROR(
                f'Path "{save_to}" is not exists or not dir, Try param "--save-to" to set.'))
            return

        self.stdout.write(self.style.WARNING(f'keysize={key_size}'))

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        try:
            private_key, public_key = generate_rsa_key(key_size=key_size)
        except Exception as exc:
            raise CommandError(f"Error, {str(exc)}.")

        pri_file = path_dir.joinpath(f'rsa_private.key')
        pub_file = path_dir.joinpath(f'rsa_public.key')
        self.save_to_file(private_key, file=pri_file)
        self.save_to_file(public_key, file=pub_file)

        self.stdout.write(self.style.SUCCESS(
            f"""[private_key]: \n{private_key}\n"""
            f"""[public_key]: \n{public_key}"""))

    def save_to_file(self, key: str, file: Path):
        with file.open('w') as f:
            f.write(key)

        self.stdout.write(self.style.SUCCESS(f"""Save file to: {file}"""))
