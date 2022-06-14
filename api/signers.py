from datetime import datetime
from urllib.parse import quote

from django.utils.translation import gettext as _
from rest_framework.response import Response
from rest_framework import HTTP_HEADER_ENCODING

from utils.crypto.rsa import SHA256WithRSA
from core import errors


class SignatureParser:
    def __init__(self, sign_type: str):
        self.sign_type = sign_type

    @staticmethod
    def get_header(request):
        """
        Extracts the header containing the JSON web token from the given
        request.
        """
        header = request.META.get('HTTP_AUTHORIZATION')

        if isinstance(header, str):
            # Work around django test client oddness
            header = header.encode(HTTP_HEADER_ENCODING)

        return header

    def get_raw_token(self, header) -> bytes:
        """
        Extracts an unvalidated token from the given "Authorization"
        header value.
        """
        parts = header.split()

        if len(parts) == 0:
            # Empty AUTHORIZATION header sent
            raise errors.NotAuthenticated(
                message=_('未提供身份认证标头"Authorization"')
            )

        if parts[0] != self.sign_type.encode(HTTP_HEADER_ENCODING):
            # Assume the header does not contain a token
            raise errors.AuthenticationFailed(
                message=_('身份认证类型不支持'),
            )

        if len(parts) != 2:
            raise errors.AuthenticationFailed(
                message=_('授权标头"Authorization"值格式无效，必须是空格分隔的两个值组成的')
            )

        return parts[1]

    def get_token_in_header(self, request):
        header = self.get_header(request)
        token = self.get_raw_token(header)
        return token.decode('utf-8')

    def parse_token(self, token: str):
        """
        :raises: AuthenticationFailed, NotAuthenticated
        """
        parts = token.split(',')
        if len(parts) != 4:
            raise errors.AuthenticationFailed(
                message=_('授权标头值格式无效')
            )

        sign_type, app_id, timestamp, signature = parts
        if sign_type != self.sign_type:
            raise errors.AuthenticationFailed(
                message=_('身份认证类型不支持'),
            )

        try:
            timestamp = int(timestamp)
        except ValueError:
            raise errors.AuthenticationFailed(
                message=_('授权标头值时间戳格式无效')
            )

        now_timestamp = datetime.now().timestamp()
        now_timestamp = int(now_timestamp)
        if abs(now_timestamp - timestamp) > 60:
            raise errors.AuthenticationFailed(
                message=_('授权标头值无效，时间戳一分钟内有效。')
            )

        return sign_type, app_id, timestamp, signature


class SignatureRequest:
    SING_TYPE = 'SHA256-RSA2048'

    def __init__(self, request, public_key: str):
        self.request = request
        self.public_key = public_key
        try:
            self.rsa = SHA256WithRSA(public_key=self.public_key)
        except (TypeError, ValueError) as e:
            raise errors.ConflictError(
                message=_('无效的公钥') + str(e), code='InvalidRSAPublicKey'
            )

    @staticmethod
    def string_to_sign(method: str, uri: str, timestamp: int, body: str):
        """
        认证类型\n
        请求时间戳\n
        HTTP请求方法\n
        URI\n
        请求报文主体\n
        """
        return '\n'.join([
            SignatureRequest.SING_TYPE,
            str(timestamp),
            method.upper(),
            quote(uri),
            body
        ])

    @staticmethod
    def sign(sign_string: str, private_key: str):
        rsa = SHA256WithRSA(private_key=private_key)
        return rsa.sign(sign_string.encode('utf-8'))

    @staticmethod
    def built_token(app_id: str, method: str, uri: str, body: str, private_key: str):
        """
        authentication_type,app_id,timestamp,signature
        """
        timestamp = datetime.now().timestamp()
        sign_string = SignatureRequest.string_to_sign(
            method=method, uri=uri, timestamp=int(timestamp), body=body
        )
        signature = SignatureRequest.sign(sign_string=sign_string, private_key=private_key)
        return ','.join([
            SignatureRequest.SING_TYPE,
            app_id,
            str(int(timestamp)),
            signature
        ])

    def verify(self, data: bytes, sig: str):
        """
        :return:
            True
            False
        """
        return self.rsa.verify(signature=sig, data=data)

    def verify_signature(self, timestamp: int, method: str, uri: str, body: str, sig: str):
        """
        :return:
            True
            False
        """
        sign_string = self.string_to_sign(
            method=method, uri=uri, timestamp=timestamp, body=body
        )
        return self.verify(data=sign_string.encode('utf-8'), sig=sig)


class SignatureResponse:
    SING_TYPE = 'SHA256-RSA2048'

    def __init__(self, private_key: str):
        self.private_key = private_key

    @staticmethod
    def string_to_sign(sign_type: str, timestamp: int, body: str):
        """
        认证类型\n
        应答时间戳\n
        请求报文主体\n
        """
        return '\n'.join([
            sign_type,
            str(timestamp),
            body
        ])

    @staticmethod
    def sign(sign_string: str, private_key: str):
        rsa = SHA256WithRSA(private_key=private_key)
        return rsa.sign(sign_string.encode('utf-8'))

    def built_signature(self, body: str, timestamp: int):
        sign_string = self.string_to_sign(
            sign_type=self.SING_TYPE, timestamp=timestamp, body=body
        )
        return self.sign(sign_string=sign_string, private_key=self.private_key)

    def add_sign(self, response: Response):
        timestamp = datetime.now().timestamp()
        timestamp = int(timestamp)
        body = response.rendered_content
        signature = self.built_signature(body=body.decode('utf-8'), timestamp=timestamp)
        response['Pay-Timestamp'] = timestamp
        response['Pay-Signature'] = signature
        response['Pay-Sign-Type'] = self.SING_TYPE
        return response

    @staticmethod
    def verify(data: bytes, sig: str, public_key: str):
        """
        :return:
            True
            False
        """
        rsa = SHA256WithRSA(public_key=public_key)
        return rsa.verify(signature=sig, data=data)
