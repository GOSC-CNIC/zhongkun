from __future__ import print_function
import ipaddress

from django.core.management.base import BaseCommand
import requests
from scan.managers import ScannerManager, TaskManager, URLHTTPValidator
from core import errors


class Command(BaseCommand):
    help = "run this command to add, enable, disable the scanner or add task"

    def add_arguments(self, parser):
        parser.add_argument(
            "subcommand",
            choices=["addscanner", "enablescanner", "disablescanner", "addtask"],
        )
        parser.add_argument(
            "--name",
            nargs="?",
            help="scanner or task name.",
        )
        parser.add_argument(
            "--ipaddr",
            nargs="?",
            help="scanner or task ipaddr.",
        )
        parser.add_argument(
            "--port",
            nargs="?",
            help="scanner port.",
        )
        parser.add_argument(
            "--status",
            nargs="?",
            help="scanner status.",
        )
        parser.add_argument(
            "--url",
            nargs="?",
            help="task url.",
        )
        parser.add_argument(
            "--priority",
            default=2,
            nargs="?",
            help="task priority, default is 2.",
        )
        parser.add_argument(
            "--type", nargs="?", help="scanner or task type.", choices=["web", "host"]
        )
        parser.add_argument(
            "--engine", nargs="?", help="scanner engine.", choices=["zap", "gvm"]
        )
        parser.add_argument(
            "--key",
            nargs="?",
            help="scanner key.",
        )
        parser.add_argument(
            "--max_concurrency",
            nargs="?",
            help="scanner max scan concurrency.",
        )

    def handle(self, *args, **options):
        """
        Dispatches by given subcommand
        """
        if options["subcommand"] == "addscanner":
            self.add_scanner(options=options)
        elif options["subcommand"] == "disablescanner":
            self.disable_scanner(options=options)
        elif options["subcommand"] == "enablescanner":
            self.enable_scanner(options=options)
        elif options["subcommand"] == "addtask":
            self.add_task(options=options)
        else:
            print(self.help)

    def add_task(self, options):
        name = options["name"]
        type = options["type"]
        if type not in ["web", "host"]:
            self.stdout.write(self.style.ERROR("Task type invalid."))
            return
        target = options["url"] if type == "web" else options["ipaddr"]
        if not target:
            self.stdout.write(self.style.ERROR("Task target invalid."))
            return
        try:
            if type == "web":
                URLHTTPValidator()(target)
            if type == "host":
                ipaddress.IPv4Address(target)
            priority = options["priority"]
            priority = 2 if not priority else int(priority)
            remark = "Created by command"
            TaskManager.create_task_command(
                name=name, type=type, target=target, remark=remark, priority=priority
            )
            self.stdout.write(self.style.SUCCESS(f"Create task {name} success."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Task information invalid. {str(e)}"))

    def enable_scanner(self, options):
        name = options["name"]
        try:
            scanner = ScannerManager.get_scanner(name=name)
            if not self._check_scanner(
                ipaddr=scanner.ipaddr,
                port=scanner.port,
                engine=scanner.engine,
                key=scanner.key,
            ):
                self.stdout.write(self.style.ERROR(f"Scanner {name} not access."))
            ScannerManager.enable_scanner(scanner=scanner)
            self.stdout.write(self.style.SUCCESS(f"Scanner {name} enabled."))
        except errors.NotFound:
            self.stdout.write(self.style.ERROR(f"Scanner {name} not found."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))

    def disable_scanner(self, options):
        name = options["name"]
        try:
            scanner = ScannerManager.get_scanner(name=name)
            ScannerManager.disable_scanner(scanner=scanner)
            self.stdout.write(self.style.SUCCESS(f"Scanner {name} disabled."))
        except errors.NotFound:
            self.stdout.write(self.style.ERROR(f"Scanner {name} not found."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))

    def add_scanner(self, options):
        name = options["name"]
        ipaddr = options["ipaddr"]
        port = options["port"]
        type = options["type"]
        engine = options["engine"]
        status = options["status"]
        key = options["key"]
        max_concurrency = options["max_concurrency"]
        if not engine or not key:
            self.stdout.write(self.style.ERROR(f"Scanner information not provide."))
            return
        if type not in ["web", "host"]:
            self.stdout.write(self.style.ERROR("Scanner type invalid."))
            return
        if status not in ["enable", "disable"]:
            self.stdout.write(self.style.ERROR("Scanner status invalid."))
            return

        try:
            ipaddress.IPv4Address(ipaddr)
            port = int(port)
            max_concurrency = int(max_concurrency)
        except ipaddress.AddressValueError:
            self.stdout.write(self.style.ERROR("Scanner address invalid."))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR("Scanner number invalid."))
            return

        if status == "enable" and not self._check_scanner(
            ipaddr=ipaddr, port=port, engine=engine, key=key
        ):
            self.stdout.write(self.style.ERROR(f"Scanner {name} not access."))
            return
        try:
            ScannerManager.create_scanner(
                name=name,
                type=type,
                ipaddr=ipaddr,
                port=port,
                key=key,
                engine=engine,
                max_concurrency=max_concurrency,
                status=status,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Create scanner failed. {str(e)}"))
            return
        self.stdout.write(self.style.SUCCESS(f"Scanner {name} created."))

    def _check_scanner(self, ipaddr, port, engine, key):
        url = f"http://{ipaddr}:{port}/{engine}/hello"
        try:
            response = requests.get(url, headers={"secret-key": key})
            response.raise_for_status()
            data = response.json()
            if not data["ok"]:
                raise Exception()
            return True
        except Exception as e:
            self.stdout.write(f"Check scanner failed.")
            return False
