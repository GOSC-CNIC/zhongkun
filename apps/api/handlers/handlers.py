from urllib.parse import quote as urlquote

from django.http import FileResponse
from django.urls import reverse
from rest_framework.response import Response

from utils import storagers
from utils import time
from core import errors as exceptions


class MediaHandler:
    @staticmethod
    def media_upload(view, request, kwargs):
        paths = kwargs.get(view.lookup_field, '').rsplit('/', maxsplit=1)
        if len(paths) == 2:
            storage_to, filename = paths
        else:
            storage_to, filename = '', paths[-1]

        request.upload_handlers = [
            storagers.Md5TemporaryFileUploadHandler(request=request),
            storagers.Md5MemoryFileUploadHandler(request=request)
        ]

        content_md5 = view.request.headers.get('Content-MD5', '')
        if not content_md5:
            return view.exception_response(exc=exceptions.InvalidDigest())

        content_length = request.headers.get('content-length')
        if not content_length:
            return view.exception_response(
                exc=exceptions.BadRequest(
                    message='header "Content-Length" is required'))

        try:
            content_length = int(content_length)
        except (ValueError, TypeError):
            raise exceptions.BadRequest(
                message='header "Content-Length" is invalid')

        try:
            request.parser_context['kwargs']['filename'] = filename
            put_data = request.data
        except Exception as exc:
            return view.exception_response(exceptions.Error.from_error(exc))

        file = put_data.get('file')
        if not file:
            return view.exception_response(
                exc=exceptions.BadRequest(message='Request body is empty.'))

        if content_length != file.size:
            return view.exception_response(
                exc=exceptions.BadRequest(
                    message='The length of body not same header "Content-Length"'))

        if content_md5 != file.file_md5:
            return view.exception_response(
                exc=exceptions.BadDigest())

        return MediaHandler._storage_media(view=view, subpath=storage_to,
                                           filename=filename, file=file)

    @staticmethod
    def _storage_media(view, subpath: str, filename: str, file):
        if storagers.LogoFileStorager.is_start_prefix(sub_path=subpath):
            filename = storagers.LogoFileStorager.storage_filename(filename=filename, md5=file.file_md5)
            storager = storagers.LogoFileStorager(filename=filename)
        elif storagers.CertificationFileStorager.is_start_prefix(sub_path=subpath):
            filename = storagers.CertificationFileStorager.storage_filename(filename=filename, md5=file.file_md5)
            storager = storagers.CertificationFileStorager(filename=filename)
        else:
            storager = storagers.MediaFileStorager(filename=filename, storage_to=subpath)

        try:
            storager.save_file(file)
        except Exception as exc:
            storager.delete()
            return view.exception_response(exc)

        api_path = reverse('api:media-detail', kwargs={'url_path': storager.relative_path()})
        return Response(data={'url_path': api_path})

    @staticmethod
    def media_download(view, request, kwargs):
        path = kwargs.get(view.lookup_field, '')
        paths = path.rsplit('/', maxsplit=1)
        if len(paths) == 2:
            storage_to, filename = paths
        else:
            storage_to, filename = '', paths[-1]

        if not bool(request.user and request.user.is_authenticated):
            if not (storage_to == 'logo' or storage_to.startswith('logo/')):
                return view.exception_response(exceptions.AccessDenied(message='未认证'))

        return MediaHandler.media_download_response(
            view=view, subpath=storage_to, filename=filename)

    @staticmethod
    def media_download_response(view, subpath: str, filename: str):
        storager = storagers.MediaFileStorager(
            filename=filename, storage_to=subpath)

        if not storager.is_exists():
            return view.exception_response(exc=exceptions.NotFound())

        filesize = storager.size()
        file_generator = storager.get_file_generator()
        last_modified = time.time_to_gmt(storager.last_modified_time())

        filename = urlquote(filename)  # 中文文件名需要
        response = FileResponse(file_generator)
        response['Content-Length'] = filesize
        response['Content-Type'] = 'application/octet-stream'  # 注意格式
        response['Content-Disposition'] = f"attachment;filename*=utf-8''{filename}"  # 注意filename 这个是下载后的名字
        response['Cache-Control'] = 'max-age=20'

        if last_modified:
            response['Last-Modified'] = last_modified

        return response
