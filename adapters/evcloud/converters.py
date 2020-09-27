import re
from datetime import datetime, timedelta, timezone
from pytz import utc

from .. import outputs
from .utils import get_exp_jwt


datetime_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$'
)


def get_fixed_timezone(offset):
    """Return a tzinfo instance with a fixed offset from UTC."""
    if isinstance(offset, timedelta):
        offset = offset.total_seconds() // 60
    sign = '-' if offset < 0 else '+'
    hhmm = '%02d%02d' % divmod(abs(offset), 60)
    name = sign + hhmm
    return timezone(timedelta(minutes=offset), name)


def parse_datetime(value):
    """Parse a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.

    Raise ValueError if the input is well formatted but not a valid datetime.
    Return None if the input isn't well formatted.
    """
    match = datetime_re.match(value)
    if match:
        kw = match.groupdict()
        kw['microsecond'] = kw['microsecond'] and kw['microsecond'].ljust(6, '0')
        tzinfo = kw.pop('tzinfo')
        if tzinfo == 'Z':
            tzinfo = utc
        elif tzinfo is not None:
            offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
            offset = 60 * int(tzinfo[1:3]) + offset_mins
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = get_fixed_timezone(offset)
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        kw['tzinfo'] = tzinfo
        return datetime(**kw)


def iso_to_datetime(value, default=datetime(year=1, month=1, day=1, hour=0, minute=0, second=0, tzinfo=utc)):
    try:
        parsed = parse_datetime(value)
        if parsed is not None:
            return default
    except (ValueError, TypeError):
        return default


class OutputConverter:
    @staticmethod
    def _server_create_output_server(vm_dict):
        """
        :return: outputs.ServerCreateOutputServer()
        """
        data = vm_dict
        image = outputs.ServerCreateOutputServerImage(
            name=data.get('image'),
            system=data.get('image')
        )
        mac_ip = data.get('mac_ip')
        if isinstance(mac_ip, str):
            server_ip = {'ipv4': mac_ip, 'public_ipv4': None}
        elif isinstance(mac_ip, dict):
            server_ip = {'ipv4': mac_ip.get('ipv4'), 'public_ipv4': mac_ip.get('public_ipv4')}
        else:
            server_ip = {'ipv4': None, 'public_ipv4': None}

        ip = outputs.ServerCreateOutputServerIP(**server_ip)
        server = outputs.ServerCreateOutputServer(
            uuid=data.get('uuid'),
            ram=data.get('mem'),
            vcpu=data.get('vcpu'),
            ip=ip,
            image=image,
            creation_time=iso_to_datetime(data.get('create_time'))
        )
        return server

    @staticmethod
    def to_server_create_output(vm_dict):
        server = OutputConverter._server_create_output_server(vm_dict)
        return outputs.ServerCreateOutput(server=server)

    @staticmethod
    def to_server_create_output_error(error=None):
        return outputs.ServerCreateOutput(ok=False, error=error, server=None)

    @staticmethod
    def to_authenticate_output_token(token: str, username: str, password: str):
        expire = (datetime.utcnow() + timedelta(hours=2)).timestamp()
        header = outputs.AuthenticateOutputHeader(header_name='Authorization', header_value=f'Token {token}')
        return outputs.AuthenticateOutput(style='token', token=token, header=header, query=None, expire=expire,
                                          username=username, password=password)

    @staticmethod
    def to_authenticate_output_jwt(token: str, username: str, password: str):
        expire = get_exp_jwt(token) - 60  # 过期时间提前60s
        if expire < 0:
            expire = (datetime.utcnow() + timedelta(hours=1)).timestamp()

        header = outputs.AuthenticateOutputHeader(header_name='Authorization', header_value=f'JWT {token}')
        return outputs.AuthenticateOutput(style='JWT', token=token, header=header, query=None, expire=expire,
                                          username=username, password=password)

    @staticmethod
    def to_authenticate_output_error(error, style: str = None, username: str = None, password: str = None):
        return outputs.AuthenticateOutput(ok=False, error=error, style=style, token='', header=None,
                                          query=None, expire=0, username=username, password=password)

    @staticmethod
    def to_server_status_output(status_code: int):
        if status_code not in outputs.ServerStatus():
            status_code = outputs.ServerStatus.NOSTATE
        status_mean = outputs.ServerStatus.get_mean(status_code)
        return outputs.ServerStatusOutput(status=status_code, status_mean=status_mean)

    @staticmethod
    def to_server_status_output_error(error):
        return outputs.ServerStatusOutput(ok=False, status=outputs.ServerStatus.NOSTATE, status_mean='', error=error)

    @staticmethod
    def to_server_vnc_output(url: str):
        return outputs.ServerVNCOutput(vnc=outputs.ServerVNCOutputVNC(url=url))

    @staticmethod
    def to_server_vnc_output_error(error):
        return outputs.ServerVNCOutput(ok=False, error=error, vnc=None)

    @staticmethod
    def to_list_image_output_error(error):
        return outputs.ListImageOutput(ok=False, error=error, images=[])

    @staticmethod
    def to_list_image_output(images: list):
        new_images = []
        for img in images:
            creation_time = iso_to_datetime(img['create_time'])
            new_img = outputs.ListImageOutputImage(id=img['id'], name=img['name'], system=img['name'], desc=img['desc'],
                                                   system_type=img['sys_type']['name'], creation_time=creation_time)
            new_images.append(new_img)

        return outputs.ListImageOutput(images=new_images)

    @staticmethod
    def to_list_network_output_error(error):
        return outputs.ListNetworkOutput(ok=False, error=error, networks=[])

    @staticmethod
    def to_list_network_output(networks: list):
        new_networks = []
        for net in networks:
            public = {0: False, 1: True}.get(net['tag'], False) if 'tag' in net else None
            new_net = outputs.ListNetworkOutputNetwork(id=net['id'], name=net['name'], public=public, segment=net['subnet_ip'])
            new_networks.append(new_net)

        return outputs.ListNetworkOutput(networks=new_networks)

    @staticmethod
    def to_server_detail_output(vm: dict):
        server = OutputConverter._server_create_output_server(vm)
        return outputs.ServerDetailOutput(server=server)

    @staticmethod
    def to_server_detail_output_error(error):
        return outputs.ServerDetailOutput(ok=False, error=error, server=None)
