import base64
import json


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
