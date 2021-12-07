import os

from django.core.management.base import BaseCommand, CommandError

from monitor.models import MonitorJobVideoMeeting, MonitorProvider


class Command(BaseCommand):
    help = """
    manage.py meetingjob --file="/filename.txt"
    
    file.txt format:
    name,name_en,tag,ip
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', default='', dest='filename', type=str,
            help='path of file',
        )

        parser.add_argument(
            # 当命令行有此参数时取值const, 否则取值default
            '--test', default=None, nargs='?', dest='test', const=True,
            help='test.',
        )
        parser.add_argument(
            # 当命令行有此参数时取值const, 否则取值default
            '--debug', default=None, nargs='?', dest='debug', const=True,
            help='debug.',
        )

    def handle(self, *args, **options):
        filename = options['filename']
        if not os.path.exists(filename):
            raise CommandError(f"File({filename}) not exist.")

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action buckets cancelled.")

        self.parse_file(filename=filename, options=options)

    def parse_file(self, filename: str, options):
        test = options.get('test', None)
        debug = options.get('debug', None)
        provider = MonitorProvider.objects.first()
        if provider is None:
            self.stdout.write(self.style.ERROR('No provider'))
            return

        self.stdout.write(self.style.SUCCESS(f'provider: {provider.name}, {provider.endpoint_url}'))
        if input('Are you sure you want to continue?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action buckets cancelled.")

        with open(filename, "r") as f:
            lines = f.readlines()
            for line in lines:
                if debug:
                    self.stdout.write(self.style.SUCCESS(f'Line: {line}'))

                items = line.split(',')
                if len(items) != 4:
                    self.stdout.write(self.style.ERROR(
                        f'Split line invalid: {items}'))
                    continue

                name, name_en, tag, ip = items

                if debug:
                    self.stdout.write(self.style.SUCCESS(
                        f'Split line: name={name}; name_en={name_en}, tag={tag}; ip={ip}'))

                if test:
                    continue

                job = MonitorJobVideoMeeting.objects.filter(name=name, name_en=name_en).first()
                if job is not None:
                    self.stdout.write(self.style.NOTICE(
                        f'Already exists: name={name}; name_en={name_en}'))
                    continue

                job = MonitorJobVideoMeeting()
                job.name = name.strip(' ')
                job.name_en=name_en.strip(' ')
                job.job_tag = tag.strip(' ')
                job.ips = ip.strip(' ')
                job.provider_id=provider.id
                job.save()

