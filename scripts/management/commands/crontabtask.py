from __future__ import print_function

from django.core.management.base import BaseCommand, CommandError

from scripts.crontab_manager import CrontabManager


class Command(BaseCommand):
    help = 'run this command to add, show, remove, run or list-setting the jobs ' \
           'defined in CRONTABJOBS setting from/to crontab'

    def add_arguments(self, parser):
        parser.add_argument('subcommand', choices=['add', 'show', 'remove', 'run', 'list-setting'])
        parser.add_argument('comment', nargs='?')
        parser.add_argument('--all', nargs='?', dest='all', const=True, help='use when "remove"')

    def handle(self, *args, **options):
        """
        Dispatches by given subcommand
        """
        comment = options['comment']
        crontab = CrontabManager()
        if options['subcommand'] == 'add':
            crontab.add_jobs(comment_start_with=comment)
        elif options['subcommand'] == 'show':
            crontab.show_jobs()
        elif options['subcommand'] == 'remove':
            _all = options['all']
            crontab.remove_jobs(comment_start_with=comment, remove_all=_all)
        elif options['subcommand'] == 'list-setting':
            crontab.list_job_settings()
        elif options['subcommand'] == 'run':
            comment = options['comment']
            if not comment:
                raise CommandError('Must be input "comment" when sub command run.')

            jobs = crontab.find_comment_start_with(start_with=comment)
            if not jobs:
                self.stdout.write(self.style.NOTICE(f'No jobs match.'))
                return

            self.stdout.write(self.style.NOTICE(f'Will run jobs:'))
            for job in jobs:
                self.stdout.write(self.style.NOTICE(str(job)))

            if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
                raise CommandError("cancelled.")

            for job in jobs:
                job.run()
        else:
            print(self.help)
