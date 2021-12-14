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

        parser.add_argument(
            # 当命令行有此参数时取值const, 否则取值default
            '--ips-strip', default=None, nargs='?', dest='ips-strip', const=True,
            help='去除ips前后的换行或空格.',
        )

    def handle(self, *args, **options):
        ips_strip = options['ips-strip']
        if ips_strip:
            self.stdout.write(self.style.NOTICE(f'Will strip ips'))
            if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
                raise CommandError("action buckets cancelled.")

            self.handle_ips(options=options)
            return

        filename = options['filename']
        if not os.path.exists(filename):
            raise CommandError(f"File({filename}) not exist.")

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
                    self.stdout.write(self.style.NOTICE(f'Already exists: name={name}; name_en={name_en}'))
                    continue

                job = MonitorJobVideoMeeting()
                job.name = name.strip(' ')
                job.name_en=name_en.strip(' ')
                job.job_tag = tag.strip(' ')
                ip = ip.replace('\n', '')
                ip = ip.replace('\r', '')
                ip = ip.replace(' ', '')
                job.ips = ip
                job.provider_id=provider.id
                job.save()

    def handle_ips(self, options):
        debug = options.get('debug', None)
        queryset = MonitorJobVideoMeeting.objects.all()
        all_count = len(queryset)
        count = 0
        for job in queryset:
            ipv4s = [i.strip(' ') for i in job.ips.split(';')]
            print(ipv4s)
            old_ips = job.ips
            new_ips = old_ips.replace('\n', '')
            new_ips = new_ips.replace('\r', '')
            new_ips = new_ips.replace(' ', '')
            new_ips = new_ips.replace(r'\n', '')
            if new_ips != job.ips:
                job.ips = new_ips
                job.save(update_fields=['ips'])
                count += 1
                if debug:
                    self.stdout.write(self.style.SUCCESS(f'meeting(id={job.id}), ips={job.ips}) -> ips={new_ips}'))

        self.stdout.write(self.style.SUCCESS(f'去除ips前后的空格或换行符,总记录数：{all_count}，有变化的数据数量：{count}'))
