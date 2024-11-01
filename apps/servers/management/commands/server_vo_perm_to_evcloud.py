from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.servers.models import Server, ServiceConfig
from apps.servers.evcloud_perms import EVCloudPermsSynchronizer


class Command(BaseCommand):
    help = """
    manage.py server_vo_perm_to_evcloud --test --server-id="xx" --all --service-id="xx" --start="2024-07-30T08:40:38+00:00"
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
            help='Filter servers with a creation time greater than or equal to "start".',
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
            self.server_vo_to_evcloud(server_id=server_id, is_test=is_test)
            return
        elif is_all:
            self.all_servers_vo_to_evcloud(creation_time_gte=start_time_gte, service_id=service_id, is_test=is_test)
            return

        raise CommandError("Nothing to do, not select servers")

    @staticmethod
    def build_server_msg(server: Server):
        return f'vo server(id={server.id}, ip={server.ipv4}, create={server.creation_time.isoformat()})'

    def server_vo_to_evcloud(self, server_id: str, is_test: bool = False):
        server = self.get_server(server_id=server_id)
        if server is None:
            raise CommandError("Server not exists.")

        msg = f"Will sync vo server({server.ipv4}) user perm to EVCloud"
        if is_test:
            msg = f'[Test], {msg}'

        self.stdout.write(self.style.NOTICE(msg))
        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action cancelled.")

        self.do_sync_servers_to_evcloud(servers=[server], is_test=is_test)

    def all_servers_vo_to_evcloud(
            self, creation_time_gte: datetime = None, service_id: str = None, is_test: bool = False
    ):
        server_qs = self.get_evcloud_vo_server_qs(creation_time_gte=creation_time_gte, service_id=service_id)
        total = server_qs.count()
        if total <= 0:
            raise CommandError(f"Nothing to do, [{total}] servers")

        if is_test:
            self.stdout.write(self.style.NOTICE(f"[Test] Will sync all [{total}] vo server user perm to EVCloud"))
        else:
            self.stdout.write(self.style.NOTICE(f"Will sync all [{total}] vo server user perm to EVCloud"))

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("action cancelled.")

        self.do_sync_servers_to_evcloud(servers=server_qs, is_test=is_test)

    def do_sync_servers_to_evcloud(self, servers, is_test: bool):
        total = len(servers)
        num = 0
        for server in servers:
            num += 1
            server_msg = self.build_server_msg(server=server)
            is_need, msg = self.is_need_sync_vo_perm(server=server)
            if not is_need:
                self.stdout.write(self.style.NOTICE(f'{num}/{total} {msg}, {server_msg}'))
                continue

            try:
                if is_test:
                    self.stdout.write(self.style.SUCCESS(f'[Test] {num}/{total} OK, {server_msg}'))
                else:
                    self.sync_one_server_vo_evcloud(server=server)
                    self.stdout.write(self.style.SUCCESS(f'{num}/{total} OK, {server_msg}'))
            except Exception as exc:
                self.stdout.write(self.style.SUCCESS(f'Failed, {server_msg}, {str(exc)}'))
                return False

    @staticmethod
    def sync_one_server_vo_evcloud(server: Server):
        EVCloudPermsSynchronizer().sync_server_perms_to_evcloud(server=server)

    @staticmethod
    def is_need_sync_vo_perm(server: Server):
        if server.classification != Server.Classification.VO.value:
            return False, 'It is not vo server'

        if server.service.service_type != ServiceConfig.ServiceType.EVCLOUD.value:
            return False, 'The service of server is not EVCloud'

        return True, ''

    @staticmethod
    def get_server(server_id: str):
        return Server.objects.select_related(
            'user', 'service', 'vo'
        ).filter(id=server_id).first()

    @staticmethod
    def get_evcloud_vo_server_qs(creation_time_gte: datetime = None, service_id: str = None):
        qs = Server.objects.select_related(
            'user', 'vo', 'service'
        ).filter(
            service__service_type=ServiceConfig.ServiceType.EVCLOUD.value,
            classification=Server.Classification.VO.value
        )

        if creation_time_gte:
            qs = qs.filter(creation_time__gte=creation_time_gte)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs.order_by('creation_time')
