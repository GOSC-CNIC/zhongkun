from django.utils import timezone as dj_timezone

from apps.servers.models import Server
from utils.model import PayType


def create_server_metadata(
        service, user, vo_id=None,
        default_user: str = 'root', default_password: str = 'password',
        classification=Server.Classification.PERSONAL, ipv4: str = '',
        expiration_time=None, public_ip: bool = False, remarks: str = '',
        pay_type: str = PayType.POSTPAID.value, vcpus: int = 2, ram: int = 1024,
        disk_size: int = 100, azone_id: str = '', img_release: str = '', img_release_version: str = '',
        creation_time=None
):
    server = Server(service=service,
                    instance_id='test',
                    remarks=remarks,
                    user=user,
                    vcpus=vcpus,
                    ram=ram,
                    disk_size=disk_size,
                    ipv4=ipv4 if ipv4 else '127.0.0.1',
                    image='test-image',
                    task_status=Server.TASK_CREATED_OK,
                    public_ip=public_ip,
                    classification=classification,
                    vo_id=vo_id,
                    image_id='',
                    image_desc='image desc',
                    default_user=default_user,
                    pay_type=pay_type,
                    creation_time=creation_time if creation_time else dj_timezone.now(),
                    azone_id=azone_id,
                    img_release=img_release,
                    img_release_version=img_release_version
                    )
    server.raw_default_password = default_password
    if expiration_time:
        server.expiration_time = expiration_time

    server.save()
    return server
