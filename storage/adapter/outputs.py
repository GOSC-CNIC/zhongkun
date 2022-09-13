from collections import namedtuple

from core.errors import Error


AuthenticateOutputHeader = namedtuple(
    'AuthHeaderClass', [
        'header_name',         # example: 'Authorization'
        'header_value'         # example: 'Token xxx', 'JWT xxx'
    ]
)


class OutputBase:
    def __init__(self, ok: bool = True, error: Error = None, **kwargs):
        """
        :param ok: True(success); False(failed/error)
        :param error: Error() if ok == False else None
        :param kwargs:
        """
        self.ok = ok
        self.error = error
        self.kwargs = kwargs

    def __getattr__(self, attr):
        try:
            return getattr(self._kwargs, attr)
        except AttributeError:
            return None


class AuthenticateOutput(OutputBase):
    def __init__(
            self, style: str, token: str, expire: int,
            header: AuthenticateOutputHeader = None,
            username: str = '', password: str = '',
            access_key: str = '', secret_key: str = '',
            **kwargs
    ):
        """
        :param style: 'token', 'jwt', 'key, ...
        :param token: token value
        :param expire: expire timestamp; type: int
        :param header: AuthenticateOutputHeader() or None
        :param username:
        :param password:
        :param kwargs:
        """
        self.style = style
        self.token = token
        self.expire = expire
        self.header = header
        self.username = username
        self.password = password
        self.access_key = access_key
        self.secret_key = secret_key
        super().__init__(**kwargs)


class BucketLockOutput(OutputBase):
    pass


class BucketCreateOutput(OutputBase):
    def __init__(
            self,
            bucket_id: str,
            bucket_name: str,
            username: str,
            **kwargs
    ):
        self.bucket_id = bucket_id
        self.bucket_name = bucket_name
        self.username = username
        super().__init__(**kwargs)


class BucketDeleteOutput(OutputBase):
    pass
