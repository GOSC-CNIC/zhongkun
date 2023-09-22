from typing import List

from django.conf import settings
from django.core.management.color import color_style

from crontab import CronTab, CronItem


class CrontabManager:
    COMMENT_START_WITH = 'task'

    def __init__(self, user='root'):
        """
        user='root' root用户任务
        user=False 系统任务
        user=True 当前用户
        """
        self.user = user
        self.cron = CronTab(user=user)  # /var/spool/cron/root
        self.style = color_style(force_color=True)

    def get_jobs_setting(self):
        jobs_settings = getattr(settings, 'CRONTABJOBS', [])
        if not jobs_settings:
            print(self.style.WARNING('Not set jobs, Can set job by settings.CRONTABJOBS = [(comment, time, command)].'))
            return []

        return jobs_settings

    def build_jobs_from_settings(self):
        tasks = []
        jobs_settings = self.get_jobs_setting()
        for job_set in jobs_settings:
            comment, frequency_time, command_line = job_set
            comment: str
            if not comment.startswith(self.COMMENT_START_WITH):
                print(self.style.WARNING(
                    f'Skip job "{job_set}", The comment of job must be start with "{self.COMMENT_START_WITH}".'))

            # 创建任务
            job = CronItem(command=command_line, comment=comment, user=self.user)
            job.cron = self.cron
            job.enable(enabled=True)
            # 设置任务执行周期
            job.setall(frequency_time)
            if not job.is_valid():
                print(self.style.NOTICE(f'The job "{job_set}" is invalid.'))

            tasks.append(job)

        return tasks

    def add_jobs(self, comment_start_with: str = None):
        jobs = self.build_jobs_from_settings()
        new_add_jobs = []
        with self.cron as cron:
            for job in jobs:
                if comment_start_with and not job.comment.startswith(comment_start_with):
                    continue

                if job not in cron.crons:
                    cron.append(item=job)
                    new_add_jobs.append(job)

        if not new_add_jobs:
            print(self.style.WARNING('Not new job is added.'))
        else:
            print(self.style.SUCCESS('New add jobs:'))
            self.print_jobs(new_add_jobs)

    def remove_jobs(self, comment_start_with: str = None, remove_all=None):
        if remove_all:
            jobs = list(self.cron.crons)
            self.cron.remove_all()
        else:
            jobs = self.find_comment_start_with(start_with=comment_start_with)
            # 清除所有定时任务
            self.cron.remove(*jobs)

        # 写入配置文件
        self.cron.write_to_user(user=self.user)  # 指定用户,删除指定用户下的crontab任务
        print(self.style.SUCCESS('Removed jobs:'))
        self.print_jobs(jobs)

    def show_jobs(self):
        lines = self.cron.render()
        for line in lines.split('\n'):
            if not line or line.startswith('#'):
                print(line)
            else:
                items = line.split('#')
                if len(items) == 2:
                    frequency_time, comment = items
                else:
                    frequency_time = items[0]
                    comment = None

                s = self.style.SUCCESS(frequency_time)
                if comment is not None:
                    s += f' # {comment}'

                print(s)

    def find_comment_start_with(self, start_with: str = None):
        if not start_with:
            start_with = self.COMMENT_START_WITH

        return [job for job in self.cron.crons if job.comment.startswith(start_with)]

    def print_jobs(self, jobs: List[CronItem]):
        for job in jobs:
            line = job.render(specials=True)
            if line and line.startswith('#'):
                print(line)
                continue

            frequency_time = job.slices.render(specials=True)
            command_line = job.command
            comment = job.comment
            print(f"{self.style.SUCCESS(frequency_time)} {self.style.WARNING(command_line)} # {comment}")

    def list_job_settings(self):
        jobs_settings = self.get_jobs_setting()
        print(self.style.WARNING('Tasks list in settings:'))
        for job_set in jobs_settings:
            comment, frequency_time, command_line = job_set
            print(f"{self.style.SUCCESS(frequency_time)} {self.style.WARNING(command_line)} # {comment}")
