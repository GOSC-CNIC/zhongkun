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
            '--insert', default=None, nargs='?', dest='insert', const=True,
            help='insert job.',
        )

        parser.add_argument(
            '--update', default=None, nargs='?', dest='update', const=True,
            help='update 经纬度.',
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

        insert = options.get('insert', None)
        if insert:
            self.insert_jobs(filename=filename, options=options)
            return

        update = options.get('update', None)
        if update:
            self.update_jobs_longitude_latitude(filename=filename, options=options)
            return

        raise CommandError("Nothing to do.")

    def _parse_line(self, line: str):
        """
        :return:
            (name, name_en, tag, ip, longitude, latitude)

        :raises: Exception
        """
        items = line.split(',')
        if len(items) != 6:
            raise Exception(f'line格式无效, {items}')

        name, name_en, tag, ip, longitude, latitude = items
        name = name.strip(' ')
        name_en = name_en.strip(' ')
        tag = tag.strip(' ')
        ip = ip.replace('\n', '')
        ip = ip.replace('\r', '')
        ip = ip.replace(' ', '')
        longitude = float(longitude)
        if not (-180 <= longitude <= 180):
            raise Exception(f'经度{longitude}无效')

        latitude = float(latitude)
        if not (-90 <= latitude <= 90):
            raise Exception(f'纬度{latitude}无效')

        return (name, name_en, tag, ip, longitude, latitude)

    def parse_file(self, filename: str, debug=False):
        """
        :return:
            [(name, name_en, tag, ip, longitude, latitude),]
        """
        ret = []
        invlaid_line_nums = []
        with open(filename, "r") as f:
            lines = f.readlines()
            for num, line in enumerate(lines):
                line_num = num + 1
                line = line.strip('\n')
                if debug:
                    self.stdout.write(self.style.SUCCESS(f'Line {line_num}: {line}'))

                try:
                    job = self._parse_line(line)
                except Exception as e:
                    invlaid_line_nums.append(line_num)
                    self.stdout.write(self.style.ERROR(f'Invalid Line {line_num}: {line};{str(e)}'))

                ret.append(job)

        if invlaid_line_nums:
            self.stdout.write(self.style.ERROR(f'All invalid line num: {invlaid_line_nums}'))

        return ret

    def insert_jobs(self, filename: str, options):
        test = options.get('test', None)
        debug = options.get('debug', None)
        provider = MonitorProvider.objects.first()
        if provider is None:
            self.stdout.write(self.style.ERROR('No provider'))
            return

        jobs = self.parse_file(filename, debug=debug)
        self.stdout.write(self.style.SUCCESS(f'all {len(jobs)} jobs'))
        self.stdout.write(self.style.SUCCESS(f'provider: {provider.name}, {provider.endpoint_url}'))
        if input('Are you sure you want to insert jobs?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action buckets cancelled.")

        for job in jobs:
            name, name_en, tag, ip, longitude, latitude = job
            if debug:
                self.stdout.write(self.style.SUCCESS(
                    f'job: name={name}; name_en={name_en}, tag={tag}; ip={ip}; '
                    f'longitude={longitude}, latitude={latitude}'))

            meeting = MonitorJobVideoMeeting.objects.filter(name=name, name_en=name_en).first()
            if meeting is not None:
                self.stdout.write(self.style.NOTICE(f'Already exists: name={name}; name_en={name_en}'))
                continue

            if test:
                continue

            meeting = MonitorJobVideoMeeting()
            meeting.name = name
            meeting.name_en=name_en
            meeting.job_tag = tag
            meeting.ips = ip
            meeting.longitude = longitude
            meeting.latitude = latitude
            meeting.provider_id=provider.id
            meeting.save()

    def update_jobs_longitude_latitude(self, filename: str, options):
        test = options.get('test', None)
        debug = options.get('debug', None)
        provider = MonitorProvider.objects.first()
        if provider is None:
            self.stdout.write(self.style.ERROR('No provider'))
            return

        jobs = self.parse_file(filename, debug=debug)
        self.stdout.write(self.style.SUCCESS(f'all {len(jobs)} jobs'))
        self.stdout.write(self.style.SUCCESS(f'provider: {provider.name}, {provider.endpoint_url}'))
        if input("Are you sure you want to update jobs longitude latitude?\n\n"
                 "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action buckets cancelled.")

        for job in jobs:
            name, name_en, tag, ip, longitude, latitude = job
            if debug:
                self.stdout.write(self.style.SUCCESS(
                    f'job: name={name}; name_en={name_en}, tag={tag}; ip={ip}; '
                    f'longitude={longitude}, latitude={latitude}'))

            meeting = MonitorJobVideoMeeting.objects.filter(name=name, name_en=name_en).first()
            if meeting is None:
                self.stdout.write(self.style.NOTICE(f'Not exists: name={name}; name_en={name_en}'))
                continue

            if test:
                continue

            meeting.longitude = longitude
            meeting.latitude = latitude
            meeting.save(update_fields=['longitude', 'latitude'])

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
