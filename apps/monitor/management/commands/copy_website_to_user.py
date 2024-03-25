from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from monitor.models import MonitorWebsite, MonitorWebsiteTask, get_str_hash
from users.models import UserProfile


class Command(BaseCommand):
    help = """
    把所有不带路径的站点监控任务给指定用户一份
    manage.py copy_website_to_user
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', default=None, dest='username', type=str,
            help='The username that tasks copy for.',
        )

    def handle(self, *args, **options):
        username = options['username']
        user = UserProfile.objects.filter(username=username).first()
        if user is None:
            self.stdout.write(self.style.ERROR(f'The user {username} not exists.'))
            raise CommandError("cancelled.")

        self.stdout.write(self.style.ERROR(f'Will copy all website tasks for user "{user.username}".'))
        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.do_run(user=user)

    def do_run(self, user):
        self.stdout.write(self.style.SUCCESS(f'Start.'))

        create_count = self.loop_task(user=user)
        self.stdout.write(self.style.SUCCESS(f'End Copy website for user "{user.username}"，数量：{create_count}.'))

        self.stdout.write(self.style.SUCCESS('Exit.'))

    def loop_task(self, user: UserProfile):
        last_creation = None
        create_count = 0
        while True:
            try:
                tasks = self.get_tasks(creation_gt=last_creation, limit=100)
                if len(tasks) <= 0:
                    break

                for task in tasks:
                    task: MonitorWebsiteTask
                    created = self.create_website_for_user(task=task, user=user)
                    if created is True:
                        create_count += 1

                    last_creation = task.creation
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'Error loop task, {str(exc)}.'))

        return create_count

    @staticmethod
    def get_tasks(creation_gt=None, limit: int = 200):
        qs = MonitorWebsiteTask.objects.order_by('creation')
        if creation_gt:
            qs = qs.filter(creation__gt=creation_gt)

        return qs[:limit]

    @staticmethod
    def create_website_for_user(task: MonitorWebsiteTask, user):
        # 用户是否已经有了此站点监控
        websites = MonitorWebsite.objects.filter(url_hash=task.url_hash, user_id=user.id).all()
        user_website = None
        for site in websites:
            site: MonitorWebsite
            if site.full_url == task.url:
                user_website = site
                break

        if user_website is not None:
            return None

        website = MonitorWebsite.objects.filter(url_hash=task.url_hash).first()
        if website is None:
            return None

        if website.uri != '/':
            return None

        nt = timezone.now()
        user_website = MonitorWebsite(
            name=website.name, scheme=website.scheme, hostname=website.hostname,
            uri=website.uri, is_tamper_resistant=website.is_tamper_resistant,
            remark=website.remark, user_id=user.id, creation=nt, modification=nt
        )
        user_website.save(force_insert=True)
        return True
