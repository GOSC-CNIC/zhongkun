from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.app_servers.models import Server, ServiceConfig
from apps.app_servers.evcloud_perms import EVCloudPermsSynchronizer


class Command(BaseCommand):
    help = """
    manage.py service_server_owner --test --server-id="xx" --all --service-id="xx" --start="2024-07-30T08:40:38+00:00"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--server-id', default=None, nargs='?', dest='server_id', const=None,
            help='The server will change owner.',
        )

        parser.add_argument(
            '--all', default=None, nargs='?', dest='all', const=True,
            help='all server.',
        )
        parser.add_argument(
            '--service-id', default=None, nargs='?', dest='service_id', const=None,
            help='Filter servers of service',
        )
        parser.add_argument(
            '--start', default=None, nargs='?', dest='start_time_gte', const=None,
            help='Filter servers with a creation time greater than or equal to "start" will change owner.',
        )

        parser.add_argument(
            # 当命令行有此参数时取值const, 否则取值default
            '--test', default=None, nargs='?', dest='test', const=True,
            help='test.',
        )

    def handle(self, *args, **options):
        is_test = options.get('test', False)
        is_all = options['all']
        server_id = options.get('server_id', None)
        service_id = options.get('service_id', None)
        start_time_gte = options.get('start_time_gte', None)
        if start_time_gte:
            try:
                start_time_gte = datetime.fromisoformat(start_time_gte)
            except Exception as exc:
                raise CommandError("invlaid start, not isoformat time.")

        if server_id:
            self.change_server_owner(server_id=server_id, is_test=is_test)
            return
        elif is_all:
            self.change_all_servers_owner(creation_time_gte=start_time_gte, service_id=service_id, is_test=is_test)
            return

        raise CommandError("Nothing to do, not select servers")

    @staticmethod
    def build_server_msg(server: Server):
        return f'server(id={server.id}, ip={server.ipv4}, create={server.creation_time.isoformat()})'

    def change_server_owner(self, server_id: str, is_test: bool = False):
        server = self.get_server(server_id=server_id)
        if server is None:
            raise CommandError("Server not exists.")

        msg = f"Will change server({server.ipv4}) owner"
        if is_test:
            msg = f'[Test], {msg}'

        self.stdout.write(self.style.NOTICE(msg))
        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action cancelled.")

        server_msg = self.build_server_msg(server=server)
        is_need, msg = self.is_need_change_owner(server=server)
        if not is_need:
            self.stdout.write(self.style.NOTICE(f'{msg}, {server_msg}'))
            return None

        try:
            if is_test:
                self.stdout.write(self.style.SUCCESS(f'[Test] OK, {server_msg}'))
            else:
                self.change_one_server_owner(server=server)
                self.stdout.write(self.style.SUCCESS(f'OK, {server_msg}'))
        except Exception as exc:
            self.stdout.write(self.style.SUCCESS(f'Failed, {server_msg}, {str(exc)}'))
            return False

        return True

    def change_all_servers_owner(
            self, creation_time_gte: datetime = None, service_id: str = None, is_test: bool = False
    ):
        server_qs = self.get_evcloud_personal_server_qs(creation_time_gte=creation_time_gte, service_id=service_id)
        total = server_qs.count()
        if total <= 0:
            raise CommandError(f"Nothing to do, [{total}] servers")

        if is_test:
            self.stdout.write(self.style.NOTICE(f"[Test] Will change all [{total}] server's owner"))
        else:
            self.stdout.write(self.style.NOTICE(f"Will change all [{total}] server's owner"))
        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action cancelled.")

        num = 0
        for server in server_qs:
            num += 1
            server_msg = self.build_server_msg(server=server)
            is_need, msg = self.is_need_change_owner(server=server)
            if not is_need:
                self.stdout.write(self.style.NOTICE(f'{num}/{total} {msg}, {server_msg}'))
                continue

            try:
                if is_test:
                    self.stdout.write(self.style.SUCCESS(f'[Test] {num}/{total} OK, {server_msg}'))
                else:
                    self.change_one_server_owner(server=server)
                    self.stdout.write(self.style.SUCCESS(f'{num}/{total} OK, {server_msg}'))
            except Exception as exc:
                self.stdout.write(self.style.SUCCESS(f'Failed, {server_msg}, {str(exc)}'))
                return False

    @staticmethod
    def change_one_server_owner(server: Server):
        """
        :raises: Exception
        """
        EVCloudPermsSynchronizer.change_server_owner_to_evcloud(server=server)

    @staticmethod
    def is_need_change_owner(server: Server):
        try:
            EVCloudPermsSynchronizer.check_need_change_server_owner(server=server)
        except Exception as exc:
            return False, str(exc)

        return True, ''

    @staticmethod
    def get_server(server_id: str):
        return Server.objects.select_related(
            'user', 'service'
        ).filter(id=server_id).first()

    @staticmethod
    def get_evcloud_personal_server_qs(creation_time_gte: datetime = None, service_id: str = None):
        qs = Server.objects.select_related(
            'user', 'vo', 'service'
        ).filter(
            service__service_type=ServiceConfig.ServiceType.EVCLOUD.value,
            classification=Server.Classification.PERSONAL.value
        )

        if creation_time_gte:
            qs = qs.filter(creation_time__gte=creation_time_gte)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs.order_by('creation_time')
