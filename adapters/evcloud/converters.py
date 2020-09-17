from datetime import datetime, timedelta

from .. import outputs
from .utils import get_exp_jwt


class OutputConverter:
    @staticmethod
    def to_create_server_output(vm_dict):
        data = vm_dict
        image = outputs.CreateServerOutputServerImage(
            name=data.get('image'),
            system=data.get('image')
        )
        ip = outputs.CreateServerOutputServerIP(
            ipv4=data.get('mac_ip'),
            public_ipv4=False
        )
        server = outputs.CreateServerOutputServer(
            uuid=data.get('uuid'),
            ram=data.get('mem'),
            vcpu=data.get('vcpu'),
            ip=ip,
            image=image,
            creation_time=data.get('create_time')
        )
        return outputs.CreateServerOutput(server=server)

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

