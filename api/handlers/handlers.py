from urllib.parse import quote as urlquote

from django.utils.translation import gettext as _
from django.http import FileResponse
from django.urls import reverse
from rest_framework.response import Response

from service.managers import (
    VmServiceApplyManager, OrganizationApplyManager,
)
from utils import storagers
from utils import time
from core import errors as exceptions
from api.serializers import serializers
from api.viewsets import serializer_error_msg


class ApplyOrganizationHandler:
    @staticmethod
    def get_list_queryset(request, is_admin: bool = False):
        """
        获取查询集

        :param request:
        :param is_admin: True: 有管理权限的申请记录查询集；False: 用户自己的申请记录查询集；
        """
        deleted = request.query_params.get('deleted', None)
        status = request.query_params.getlist('status', None)
        if not status or status == ['']:
            status = None
        if isinstance(status, list):
            if not set(status).issubset(set(OrganizationApplyManager.model.Status.values)):
                raise exceptions.InvalidArgument(message=_('参数"status"包含无效的值'))

        if deleted:
            deleted = deleted.lower()
            if deleted == 'true':
                deleted = True
            elif deleted == 'false':
                deleted = False
            else:
                deleted = None

        if is_admin:
            return OrganizationApplyManager().admin_filter_apply_queryset(
                deleted=deleted, status=status)
        else:
            return OrganizationApplyManager().filter_user_apply_queryset(
                user=request.user, deleted=deleted, status=status)

    @staticmethod
    def list_apply(view, request, kwargs):
        """
        list user机构加入申请
        """
        try:
            queryset = ApplyOrganizationHandler.get_list_queryset(request=request)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyOrganizationSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def admin_list_apply(view, request, kwargs):
        """
        管理员list机构加入申请
        """
        if not request.user.is_federal_admin():
            return view.exception_response(
                exc=exceptions.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限')))
        try:
            queryset = ApplyOrganizationHandler.get_list_queryset(request=request, is_admin=True)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyOrganizationSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create_apply(view, request, kwargs):
        """
        提交一个机构/数据中心创建申请
        """
        oa_mgr = OrganizationApplyManager()
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        count = oa_mgr.get_in_progress_apply_count(user=request.user)
        if count >= 6:
            return view.exception_response(exceptions.TooManyApply())

        try:
            apply = oa_mgr.create_apply(data=serializer.validated_data, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.ApplyOrganizationSerializer(instance=apply).data
        return Response(data=rdata)

    @staticmethod
    def apply_action(view, request, kwargs):
        """
            cancel：取消申请
            pending：挂起申请（审核中）
            reject：拒绝
            pass：通过
            delete: 删除
        """
        _action = kwargs.get('action', '').lower()
        if _action == 'pending':
            return ApplyOrganizationHandler.pending_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'cancel':
            return ApplyOrganizationHandler.cancel_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'reject':
            return ApplyOrganizationHandler.reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pass':
            return ApplyOrganizationHandler.pass_apply(view=view, request=request, kwargs=kwargs)

        return view.exception_response(
            exc=exceptions.BadRequest(message=_('不支持操作命令"{action}"').format(action=_action)))

    @staticmethod
    def pending_apply(view, request, kwargs):
        """
        挂起一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().pending_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def cancel_apply(view, request, kwargs):
        """
        取消一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().cancel_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pass_apply(view, request, kwargs):
        """
        审核通过一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def reject_apply(view, request, kwargs):
        """
        审核拒绝一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def delete_apply(view, request, kwargs):
        """
        软删除一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            OrganizationApplyManager().delete_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)


class ApplyVmServiceHandler:
    @staticmethod
    def get_list_queryset(request, is_admin: bool = False):
        """
        获取查询集

        :param request:
        :param is_admin: True: 有管理权限的申请记录查询集；False: 用户自己的申请记录查询集；

        :raises: Error
        """
        organization_id = request.query_params.get('organization', None)
        deleted = request.query_params.get('deleted', None)
        if deleted:
            deleted = deleted.lower()
            if deleted == 'true':
                deleted = True
            elif deleted == 'false':
                deleted = False
            else:
                deleted = None

        status = request.query_params.getlist('status', None)
        if not status or status == ['']:
            status = None
        if isinstance(status, list):
            if not set(status).issubset(set(VmServiceApplyManager.model.Status.values)):
                raise exceptions.InvalidArgument(message=_('参数"status"包含无效的值'))

        if is_admin:
            return VmServiceApplyManager().admin_filter_apply_queryset(
                deleted=deleted, organization_id=organization_id, status=status)
        else:
            return VmServiceApplyManager().filter_user_apply_queryset(
                user=request.user, deleted=deleted, organization_id=organization_id, status=status)

    @staticmethod
    def list_apply(view, request, kwargs):
        """
        list user云主机服务接入申请
        """
        try:
            queryset = ApplyVmServiceHandler.get_list_queryset(request=request)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyVmServiceSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def admin_list_apply(view, request, kwargs):
        """
        管理员list云主机服务接入申请
        """
        if not request.user.is_federal_admin():
            return view.exception_response(
                exc=exceptions.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限')))
        try:
            queryset = ApplyVmServiceHandler.get_list_queryset(request=request, is_admin=True)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyVmServiceSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create_apply(view, request, kwargs):
        """
        提交一个服务接入申请
        """
        vsa_mgr = VmServiceApplyManager()
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        count = vsa_mgr.get_in_progress_apply_count(user=request.user)
        if count >= 6:
            return view.exception_response(exceptions.TooManyApply())

        try:
            apply = vsa_mgr.create_apply(data=serializer.validated_data, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.ApplyVmServiceSerializer(instance=apply).data
        return Response(data=rdata)

    @staticmethod
    def apply_action(view, request, kwargs):
        """
            cancel：取消申请
            pending：挂起申请（审核中）
            first_pass：初审通过
            first_reject：初审拒绝
            test：测试
            reject：拒绝
            pass：通过
        """
        _action = kwargs.get('action', '').lower()
        if _action == 'cancel':
            return ApplyVmServiceHandler.cancel_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pending':
            return ApplyVmServiceHandler.pending_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'first_reject':
            return ApplyVmServiceHandler.first_reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'first_pass':
            return ApplyVmServiceHandler.first_pass_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'test':
            return ApplyVmServiceHandler.test_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'reject':
            return ApplyVmServiceHandler.reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pass':
            return ApplyVmServiceHandler.pass_apply(view=view, request=request, kwargs=kwargs)

        return view.exception_response(
            exc=exceptions.BadRequest(message=_('不支持操作命令"{action}"').format(action=_action)))

    @staticmethod
    def cancel_apply(view, request, kwargs):
        """
        取消一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().cancel_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pending_apply(view, request, kwargs):
        """
        挂起一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().pending_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def first_reject_apply(view, request, kwargs):
        """
        初审拒绝一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().first_reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def first_pass_apply(view, request, kwargs):
        """
        初审通过一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().first_pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def test_apply(view, request, kwargs):
        """
        测试一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply, test_msg = VmServiceApplyManager().test_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data={
            'ok': False if test_msg else True,
            'message': test_msg,
            'apply': serializer.data
        })

    @staticmethod
    def reject_apply(view, request, kwargs):
        """
        拒绝一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pass_apply(view, request, kwargs):
        """
        通过一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def delete_apply(view, request, kwargs):
        """
        软删除一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            VmServiceApplyManager().delete_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)


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
