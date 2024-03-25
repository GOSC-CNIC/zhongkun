from django.core.management.base import BaseCommand, CommandError

from monitor.models import MonitorWebsite, MonitorWebsiteTask, MonitorWebsiteVersion


class Command(BaseCommand):
    help = """
    根据用户监控任务表补全可能缺失的站点监控任务，清理可能多余的站点监控任务。
    manage.py clearwebsitetask
    """

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self.stdout.write(self.style.ERROR(f'Will clear website task.'))
        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action buckets cancelled.")

        self.do_run()

    def do_run(self):
        self.stdout.write(self.style.SUCCESS(f'Start loop task.'))
        delete_count, change_count = self.loop_task()
        self.stdout.write(self.style.SUCCESS(f'End loop task.'))

        self.stdout.write(self.style.SUCCESS(f'Start loop user website.'))
        created_count = self.loop_user_website()
        self.stdout.write(self.style.SUCCESS(f'End loop user website，创建task数：{created_count}.'))

        self.stdout.write(self.style.SUCCESS(
            f'创建task数：{created_count}，删除task数：{delete_count}，有更改的task数量：{change_count}.'))

        if (created_count + delete_count + change_count) > 0:
            vs = MonitorWebsiteVersion.get_instance()
            old_version = vs.version
            vs.version_add_1()
            self.stdout.write(self.style.SUCCESS(
                f'Task version：{old_version} to {vs.version}'))

        self.stdout.write(self.style.SUCCESS('Exit.'))

    def loop_task(self):
        last_creation = None
        delete_count = 0
        change_count = 0
        while True:
            try:
                tasks = self.get_tasks(creation_gt=last_creation, limit=100)
                if len(tasks) <= 0:
                    break

                for task in tasks:
                    task: MonitorWebsiteTask
                    changed = self.try_clear_task(task=task)
                    if changed is True:
                        delete_count += 1
                    elif changed is False:
                        change_count += 1

                    last_creation = task.creation
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'Error loop task, {str(exc)}.'))

        return delete_count, change_count

    def try_clear_task(self, task: MonitorWebsiteTask):
        """
        :return:
            True    # 删除了
            False   # 有修改
            None    # 没有改变
        """
        websites = MonitorWebsite.objects.filter(url_hash=task.url_hash).all()
        has_website = False
        is_tamper_resistant = False
        for site in websites:
            site: MonitorWebsite
            if site.full_url == task.url:
                has_website = True
                if site.is_tamper_resistant:
                    is_tamper_resistant = True

        if has_website is False:
            task.delete()
            self.stdout.write(self.style.WARNING(f'Delete task[{task.url}].'))
            return True

        if task.is_tamper_resistant != is_tamper_resistant:
            task.is_tamper_resistant = is_tamper_resistant
            task.save(update_fields='is_tamper_resistant')
            self.stdout.write(self.style.WARNING(f'Change is_tamper_resistant={is_tamper_resistant} task[{task.url}].'))
            return False

        return None

    def loop_user_website(self):
        last_creation = None
        created_count = 0
        while True:
            try:
                sites = self.get_user_websites(creation_gt=last_creation, limit=100)
                if len(sites) <= 0:
                    break

                for site in sites:
                    task: MonitorWebsiteTask
                    created = self.try_add_task_for_site(site=site)
                    if created is True:
                        created_count += 1
                        self.stdout.write(self.style.WARNING(f'Craete task for website[{site.full_url}].'))

                    last_creation = site.creation
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'Error loop user website, {str(exc)}.'))

        return created_count

    @staticmethod
    def try_add_task_for_site(site: MonitorWebsite):
        """
        :return:
            True    # 创建了
            None    # 没有改变
        """
        full_url = site.full_url
        url_hash = site.url_hash
        task = MonitorWebsiteTask.objects.filter(url_hash=url_hash, url=full_url).first()
        if task:
            return None

        # 是否有防篡改用户监控任务
        is_tamper_resistant = False
        websites = MonitorWebsite.objects.filter(url_hash=url_hash, is_tamper_resistant=True).all()
        for ws in websites:
            ws: MonitorWebsite
            if ws.full_url == full_url:
                if ws.is_tamper_resistant is True:
                    is_tamper_resistant = True
                    break

        # 尝试更新监控任务防篡改标记
        task = MonitorWebsiteTask(
            url_hash=url_hash, url=full_url,
            is_tamper_resistant=is_tamper_resistant)
        task.save(force_insert=True)
        return True

    @staticmethod
    def get_tasks(creation_gt=None, limit: int = 200):
        qs = MonitorWebsiteTask.objects.order_by('creation')
        if creation_gt:
            qs = qs.filter(creation__gt=creation_gt)

        return qs[:limit]

    @staticmethod
    def get_user_websites(creation_gt=None, limit: int = 200):
        qs = MonitorWebsite.objects.order_by('creation')
        if creation_gt:
            qs = qs.filter(creation__gt=creation_gt)

        return qs[:limit]
