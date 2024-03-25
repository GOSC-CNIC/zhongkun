from django.core.management.base import BaseCommand, CommandError

from monitor.models import MonitorWebsite, get_str_hash


class Command(BaseCommand):
    help = """
    根据用户监控任务scheme、hostname、uri字段拼接更新url字段。
    manage.py update_website_url
    """

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self.stdout.write(self.style.ERROR(f'Will update website url.'))
        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.do_run()

    def do_run(self):
        self.stdout.write(self.style.SUCCESS(f'Start.'))

        updated_count = self.loop_user_website()
        self.stdout.write(self.style.SUCCESS(f'End loop user website，更新数：{updated_count}.'))

        self.stdout.write(self.style.SUCCESS('Exit.'))

    def loop_user_website(self):
        last_creation = None
        update_count = 0
        while True:
            try:
                sites = self.get_user_websites(creation_gt=last_creation, limit=100)
                if len(sites) <= 0:
                    break

                for site in sites:
                    updated = self.try_update_site(site=site)
                    if updated is True:
                        update_count += 1

                    last_creation = site.creation
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'Error loop user website, {str(exc)}.'))

        return update_count

    def try_update_site(self, site: MonitorWebsite):
        """
        :return:
            True     # 有改变
            False    # 没有改变
        """
        full_url = site.full_url
        if not full_url:
            return False

        url_hash = get_str_hash(full_url)

        update_fields = []
        if site.url != full_url:
            site.url = full_url
            update_fields.append('url')

        if site.url_hash != url_hash:
            site.url_hash = url_hash
            update_fields.append('url_hash')

        if update_fields:
            site.save(update_fields=update_fields)
            self.stdout.write(self.style.WARNING(f'Update {update_fields} for website[{site.full_url}].'))
            return True

        return False

    @staticmethod
    def get_user_websites(creation_gt=None, limit: int = 200):
        qs = MonitorWebsite.objects.order_by('creation')
        if creation_gt:
            qs = qs.filter(creation__gt=creation_gt)

        return qs[:limit]
