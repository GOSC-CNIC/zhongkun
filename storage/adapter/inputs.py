
class InputBase:
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __getattr__(self, attr):
        try:
            return getattr(self._kwargs, attr)
        except AttributeError:
            return None


class AuthenticateInput(InputBase):
    def __init__(self, username: str, password: str, **kwargs):
        """
        :param username:
        :param password:
        :param domain:
        :param kwargs:
        """
        self.username = username
        self.password = password
        self.domain = kwargs.get('domain', 'default')
        super().__init__(**kwargs)


class BucketLockInput(InputBase):
    LOCK_FREE = 'lock-free'             # 无锁（读写正常）
    LOCK_WRITE = 'lock-write'           # 锁定写（不允许上传删除）
    LOCK_READWRITE = 'lock-readwrite'   # 锁定读写（不允许上传下载删除）
    LOCK_VALUES = [LOCK_FREE, LOCK_WRITE, LOCK_READWRITE]

    def __init__(self, bucket_name: str, lock: str, **kwargs):
        """
        :param bucket_name:
        :param lock:
        :param kwargs:
        """
        if lock not in self.LOCK_VALUES:
            raise ValueError('Invalid lock value')

        self.bucket_name = bucket_name
        self.lock = lock
        super().__init__(**kwargs)


class BucketCreateInput(InputBase):
    def __init__(self, bucket_name: str, username: str, **kwargs):
        """
        :param bucket_name:
        :param username:
        :param kwargs:
        """
        self.bucket_name = bucket_name
        self.username = username
        super().__init__(**kwargs)


class BucketDeleteInput(InputBase):
    def __init__(self, bucket_name: str, username: str, **kwargs):
        """
        :param bucket_name:
        :param username:
        :param kwargs:
        """
        self.bucket_name = bucket_name
        self.username = username
        super().__init__(**kwargs)
