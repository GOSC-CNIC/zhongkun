import hashlib
import collections
import io
import random
from string import printable

from django.urls import reverse

from utils.test import get_or_create_user, get_or_create_center

from . import MyAPITestCase, set_auth_header


def random_string(length: int = 10):
    return random.choices(printable, k=length)


def random_bytes_io(mb_num: int):
    bio = io.BytesIO()
    for i in range(1024):  # MB
        s = ''.join(random_string(mb_num))
        b = s.encode() * 1024  # KB
        bio.write(b)

    bio.seek(0)
    return bio


def calculate_md5(file):
    if hasattr(file, 'seek'):
        file.seek(0)

    md5obj = hashlib.md5()
    if isinstance(file, collections.Iterable):
        for data in file:
            md5obj.update(data)
    else:
        for data in chunks(file):
            md5obj.update(data)

    _hash = md5obj.hexdigest()
    return _hash


def chunks(f, chunk_size=2 * 2 ** 20):
    """
    Read the file and yield chunks of ``chunk_size`` bytes (defaults to
    ``File.DEFAULT_CHUNK_SIZE``).
    """
    try:
        f.seek(0)
    except AttributeError:
        pass

    while True:
        data = f.read(chunk_size)
        if not data:
            break
        yield data


class RegistryTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.data_center = get_or_create_center()

    def test_list_registry(self):
        url = reverse('api:registry-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('registries', response.data)
        self.assertIsInstance(response.data['registries'], list)
        self.assertKeysIn(["id", "name", "sort_weight", "creation_time", "status", "desc", 'longitude', 'latitude'],
                          response.data['registries'][0])


class MediaApiTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)

    def download_media_response(self, url_path: str):
        url = url_path  # reverse('api:media-detail', kwargs={'url_path': url_path})
        return self.client.get(url)

    @staticmethod
    def put_media_response(client, url_path: str, file):
        """200 ok"""
        url = reverse('api:media-detail', kwargs={'url_path': url_path})
        file_md5 = calculate_md5(file)
        headers = {'HTTP_Content_MD5': file_md5}
        file.seek(0)
        return client.put(url, data=file.read(),
                          content_type='application/octet-stream', **headers)

    def test_put_logo(self):
        prefix = 'logo'
        self.upload_download_test(prefix=prefix, is_return_md5_name=True)
        prefix = 'certification'
        self.upload_download_test(prefix=prefix, is_return_md5_name=True)
        prefix = 'test'
        self.upload_download_test(prefix=prefix, is_return_md5_name=False)

    def upload_download_test(self, prefix: str, is_return_md5_name: bool):
        file = random_bytes_io(mb_num=8)
        file_md5 = calculate_md5(file)
        ext = 'jpg'
        key = f'v2test.{ext}'
        response = self.put_media_response(self.client, url_path=f'{prefix}/{key}', file=file)
        self.assertEqual(response.status_code, 200)
        if is_return_md5_name:
            filename = f'{file_md5}.{ext}'
        else:
            filename = key

        response_url_path = reverse('api:media-detail', kwargs={'url_path': f'{prefix}/{filename}'})
        self.assertEqual(response.data['url_path'], response_url_path)

        url_path = response.data['url_path']
        response = self.download_media_response(url_path=url_path)
        self.assertEqual(response.status_code, 200)
        download_md5 = calculate_md5(response)
        self.assertEqual(download_md5, file_md5, msg='Compare the MD5 of upload file and download file')
