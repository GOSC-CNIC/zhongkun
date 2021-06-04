import hashlib
import os

from django.core.files.uploadhandler import (
    MemoryFileUploadHandler,
    TemporaryFileUploadHandler
)
from django.conf import settings


def chunks(fd, chunk_size=10*1024**2):
    """
    Read the file and yield chunks of ``chunk_size`` bytes
    """
    try:
        fd.seek(0)
    except AttributeError:
        pass

    while True:
        d = fd.read(chunk_size)
        if not d:
            break

        yield d


class FileMD5Handler:
    """
    MD5计算
    """
    def __init__(self):
        self.md5_hash = hashlib.md5()
        self.start_offset = 0       # 下次输入数据开始偏移量
        self.is_valid = True

    def __getattr__(self, item):
        return getattr(self.md5_hash, item)

    def update(self, offset: int, data: bytes):
        """
        md5计算需要顺序输入文件的数据，否则MD5计算无效
        """
        if not self.is_valid:
            return

        data_len = len(data)
        if offset < 0:
            if data_len > 0:
                self.set_invalid()
            return

        if data_len == 0:
            return

        start_offset = self.start_offset
        if start_offset == offset:
            self.md5_hash.update(data)
            self.start_offset = start_offset + data_len
            return
        elif start_offset < offset:    # 计算无效
            self.set_invalid()
            return

        will_offset = offset + data_len
        if will_offset <= start_offset:   # 数据已输入过了
            return

        cut_len = will_offset - start_offset
        self.md5_hash.update(data[-cut_len:])   # 输入start_offset开始的部分数据
        self.start_offset = will_offset

    @property
    def hex_md5(self):
        if self.is_valid:
            return self.md5_hash.hexdigest()

        return ''

    def set_invalid(self):
        self.is_valid = True


class Md5MemoryFileUploadHandler(MemoryFileUploadHandler):
    chunk_size = 2 * 2 ** 20    # 2Mb

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        if self.activated:
            self.file_md5_handler = FileMD5Handler()

    def receive_data_chunk(self, raw_data, start):
        """Add the data to the BytesIO file."""
        if self.activated and self.file_md5_handler:
            self.file_md5_handler.update(offset=start, data=raw_data)

        return super().receive_data_chunk(raw_data=raw_data, start=start)

    def file_complete(self, file_size):
        f = super().file_complete(file_size=file_size)
        f.file_md5_handler = self.file_md5_handler
        f.file_md5 = self.file_md5_handler.hex_md5
        return f


class Md5TemporaryFileUploadHandler(TemporaryFileUploadHandler):
    chunk_size = 2 * 2 ** 20  # 2Mb

    def new_file(self, *args, **kwargs):
        """
        Create the file object to append to as data is coming in.
        """
        super().new_file(*args, **kwargs)
        self.file_md5_handler = FileMD5Handler()

    def receive_data_chunk(self, raw_data, start):
        super().receive_data_chunk(raw_data=raw_data, start=start)
        self.file_md5_handler.update(offset=start, data=raw_data)

    def file_complete(self, file_size):
        f = super().file_complete(file_size=file_size)
        f.file_md5_handler = self.file_md5_handler
        f.file_md5 = self.file_md5_handler.hex_md5
        return f


class MediaFileStorager:
    """
    上传media文件存储, 存储根目录为 settings.MEDIA_ROOT
    """
    prefix = 'upload'

    def __init__(self, filename, storage_to=None):
        """
        :param storage_to: subdir
        """
        self._filename = filename
        self._storage_to = storage_to if storage_to is not None else self.prefix
        self._absolute_storage_to = os.path.join(settings.MEDIA_ROOT, self._storage_to)
        self._file_absolute_path = os.path.join(self._absolute_storage_to, self._filename)

    @classmethod
    def is_start_prefix(cls, sub_path: str):
        prefix = cls.prefix
        return bool(sub_path == prefix or sub_path.startswith(prefix + '/'))

    def filename(self):
        return self._filename

    def relative_path(self):
        return os.path.join(self._storage_to, self._filename)

    def _pre_write(self):
        # 路径不存在时创建路径
        if not os.path.exists(self._absolute_storage_to):
            os.makedirs(self._absolute_storage_to)

    def save_file(self, file):
        self._pre_write()
        with open(self._file_absolute_path, 'wb') as f:
            for chunk in chunks(file):
                f.write(chunk)

    def write(self, chunk, offset=0):
        self._pre_write()
        with open(self._file_absolute_path, 'ab+') as f:
            f.seek(offset, 0)   # 文件的开头作为移动字节的参考位置
            for chunk in chunk.chunks():
                f.write(chunk)

    def is_exists(self):
        return os.path.exists(self._file_absolute_path)

    def read(self, read_size, offset=0):
        # 检查文件是否存在
        if not self.is_exists():
            return False

        try:
            with open(self._file_absolute_path, 'rb') as f:
                f.seek(offset, 0)   # 文件的开头作为移动字节的参考位置
                data = f.read(read_size)
        except:
            return False

        return data

    def size(self):
        try:
            fsize = os.path.getsize(self._file_absolute_path)
        except FileNotFoundError:
            return -1

        return fsize

    def delete(self):
        # 删除文件
        try:
            os.remove(self._file_absolute_path)
        except FileNotFoundError:
            pass

    def last_modified_time(self):
        return os.stat(self._file_absolute_path).st_mtime

    def get_file_generator(self, chunk_size=2*1024*1024):
        """
        获取读取文件生成器
        :param chunk_size: 每次迭代返回的数据块大小，type: int
        :return:
            success: a generator function to read file
            error: None
        """
        if chunk_size <= 0:
            chunk_size = 2 * 1024 * 1024    # 2MB

        # 文件是否存在
        if not os.path.exists(self._file_absolute_path):
            return None

        def file_generator(size=chunk_size):
            with open(self._file_absolute_path, 'rb') as f:
                while True:
                    chunk = f.read(size)
                    if chunk:
                        yield chunk
                    else:
                        break

        return file_generator()


class Md5FileStorager(MediaFileStorager):
    @staticmethod
    def storage_filename(filename: str, md5: str):
        r = filename.rsplit('.', maxsplit=1)
        if len(r) == 2:
            ext = r[-1].lower()
            return f'{md5}.{ext}'

        return md5


class LogoFileStorager(Md5FileStorager):
    prefix = 'logo'

    def __init__(self, filename):
        super().__init__(filename=filename)


class CertificationFileStorager(Md5FileStorager):
    prefix = 'certification'

    def __init__(self, filename):
        super().__init__(filename=filename)
