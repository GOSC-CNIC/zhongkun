import hmac
import datetime
import uuid
from base64 import b64encode
from hashlib import sha1
from urllib.parse import quote

from .model import Request


SIGV1_TIMESTAMP = '%Y%m%dT%H%M%SZ'


class Credentials:
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key


class BaseSigner:
    def __init__(self, credentials: Credentials):
        self.credentials = credentials

    def add_auth(self, request: Request):
        raise NotImplementedError('add_auth must be implemented')


class SignV1Auth(BaseSigner):
    SignatureVersion = '1.0'
    SignatureMethod = 'HMAC-SHA1'

    def __init__(self, credentials: Credentials):
        super().__init__(credentials)

    def add_auth(self, request: Request):
        datetime_now = datetime.datetime.utcnow()
        request.add_param('Timestamp', datetime_now.strftime(SIGV1_TIMESTAMP))
        request.add_param('SignatureVersion', self.SignatureVersion)
        request.add_param('SignatureMethod', self.SignatureMethod)
        request.add_param('AccessKeyId', self.credentials.access_key)
        request.add_param('SignatureNonce', uuid.uuid1().hex)

        signature = self.signature(request)
        request.add_param('Signature', signature)

    def signature(self, request):
        string_to_sign = self.string_to_sign(request)
        data = self._sign(key=self.credentials.secret_key, msg=string_to_sign)
        return b64encode(data).decode(encoding='utf-8')

    @staticmethod
    def uri_encode(s: str, encode_slash=True):
        if encode_slash:
            return quote(s, safe='-._~')

        return quote(s, safe='/-._~')

    def _canonical_query_string_params(self, params):
        li = []
        for param in sorted(params):
            value = str(params[param])
            li.append(f'{self.uri_encode(param)}={self.uri_encode(value)}')

        cqs = '&'.join(li)
        return cqs

    def string_to_sign(self, request):
        query_str = self._canonical_query_string_params(request.params)
        query_encode = self.uri_encode(query_str)
        method = request.method.upper()
        percent_encode = self.uri_encode('/')
        return f'{method}&{percent_encode}&{query_encode}'

    def _sign(self, key: str, msg: str, hex=False):
        key = key + '&'
        key = key.encode('utf-8')
        if hex:
            sig = hmac.new(key, msg.encode('utf-8'), sha1).hexdigest()
        else:
            sig = hmac.new(key, msg.encode('utf-8'), sha1).digest()
        return sig
