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


class BucketStatsOutput(OutputBase):
    def __init__(
            self,
            bucket_name: str,
            username: str,
            objects_count: int,
            bucket_size_byte: int,
            stats_time,
            **kwargs
    ):
        """
        :param bucket_name: 存储桶名称
        :param username: 存储桶的所有者名
        :param objects_count: 存储桶内对象数量
        :param bucket_size_byte: 存储桶内对象总大小，单位字节
        :param stats_time: 统计时间，datetime
        """
        self.bucket_name = bucket_name
        self.username = username
        self.objects_count = objects_count
        self.bucket_size_byte = bucket_size_byte
        self.stats_time = stats_time
        super().__init__(**kwargs)

    @property
    def bucket_size_gib(self) -> float:
        return self.bucket_size_byte / 1024**3


class VersionOutput(OutputBase):
    def __init__(
            self,
            version: str,
            **kwargs
    ):
        self.version = version
        super().__init__(**kwargs)
