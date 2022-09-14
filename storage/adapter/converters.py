import base64
import json
from datetime import datetime, timedelta

from . import outputs


def base64url_decode(data):
    if isinstance(data, str):
        data = data.encode('ascii')

    rem = len(data) % 4

    if rem > 0:
        data += b'=' * (4 - rem)

    return base64.urlsafe_b64decode(data)


def get_exp_jwt(jwt: str):
    """
    从jwt获取过期时间expire
    :param jwt:
    :return:
        int     # timestamp
        0       # if error
    """
    jwt = jwt.encode('utf-8')

    try:
        signing_input, crypto_segment = jwt.rsplit(b'.', 1)
        header_segment, payload_segment = signing_input.split(b'.', 1)
    except ValueError:
        return 0

    try:
        payload = base64url_decode(payload_segment)
    except Exception:
        return 0

    payload = json.loads(payload.decode('utf-8'))
    if 'exp' not in payload:
        return 0

    try:
        return int(payload['exp'])
    except:
        return 0


class OutputConverter:
    @staticmethod
    def to_authenticate_output_jwt(token: str, username: str, password: str):
        expire = get_exp_jwt(token) - 60  # 过期时间提前60s
        if expire < 0:
            expire = (datetime.utcnow() + timedelta(hours=1)).timestamp()

        header = outputs.AuthenticateOutputHeader(header_name='Authorization', header_value=f'Bearer {token}')
        return outputs.AuthenticateOutput(
            style='JWT', token=token, header=header, query=None, expire=expire,
            username=username, password=password
        )

    @staticmethod
    def to_authenticate_output_error(error, style: str = None, username: str = None, password: str = None):
        return outputs.AuthenticateOutput(
            ok=False, error=error, style=style, token='', header=None,
            query=None, expire=0, username=username, password=password
        )

    @staticmethod
    def to_bucket_create_output(data: dict):
        username = data.get('user', {}).get('username', '')
        return outputs.BucketCreateOutput(
            bucket_id=str(data['id']), bucket_name=data['name'], username=username
        )

    @staticmethod
    def to_bucket_create_output_error(error):
        return outputs.BucketCreateOutput(
            ok=False, error=error, bucket_id='', bucket_name='', username=''
        )
