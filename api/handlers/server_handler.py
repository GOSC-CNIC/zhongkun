from django.utils.translation import gettext as _
from django.db import transaction
from rest_framework.response import Response

from core import errors as exceptions
from core.taskqueue import server_build_status
from service.managers import ServiceManager
from servers.models import Server
from servers.managers import ServerManager, ServerArchiveManager
from api import paginations
from api.viewsets import CustomGenericViewSet
from api import serializers
from vo.managers import VoManager
from adapters import inputs
from .handlers import serializer_error_msg


class ServerHandler:
    @staticmethod
    def list_servers(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        username = request.query_params.get('username')
        user_id = request.query_params.get('user-id')
        vo_id = request.query_params.get('vo-id')

        if (username or user_id) and vo_id:
            return view.exception_response(exceptions.BadRequest(
                message=_('参数“vo-id”不能和“user-id”、“username”之一同时提交')))

        if view.is_as_admin_request(request):
            try:
                servers = ServerManager().get_admin_servers_queryset(
                    user=request.user, service_id=service_id, user_id=user_id, username=username, vo_id=vo_id)
            except Exception as exc:
                return view.exception_response(exceptions.convert_to_error(exc))
        else:
            if user_id or username or vo_id:
                return view.exception_response(exceptions.BadRequest(
                    message=_('参数“user-id”、“user-id”和“vo-id”只能和参数“as-admin”一起提交')))

            servers = ServerManager().get_user_servers_queryset(user=request.user, service_id=service_id)

        service_id_map = ServiceManager.get_service_id_map(use_cache=True)
        paginator = paginations.ServersPagination()
        try:
            page = paginator.paginate_queryset(servers, request, view=view)
            serializer = serializers.ServerSerializer(page, many=True, context={'service_id_map': service_id_map})
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def list_vo_servers(view, request, kwargs):
        vo_id = kwargs.get('vo_id')
        service_id = request.query_params.get('service_id', None)

        vo_mgr = VoManager()
        vo = vo_mgr.get_vo_by_id(vo_id)
        if vo is None:
            raise exceptions.NotFound(message=_('项目组不存在'))

        try:
            vo_mgr.check_read_perm(vo=vo, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        servers = ServerManager().get_vo_servers_queryset(vo_id=vo_id, service_id=service_id)

        service_id_map = ServiceManager.get_service_id_map(use_cache=True)
        paginator = paginations.ServersPagination()
        try:
            page = paginator.paginate_queryset(servers, request, view=view)
            serializer = serializers.ServerSerializer(page, many=True, context={'service_id_map': service_id_map})
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def server_lock(view, request, kwargs):
        server_id = kwargs.get(view.lookup_field, '')
        lock = request.query_params.get('lock', None)
        if lock is None:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"lock"必须提交的')))

        if lock not in Server.Lock.values:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"lock"的值无效')))

        try:
            server = ServerManager().get_read_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        try:
            server.lock = lock
            server.save(update_fields=['lock'])
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'lock': lock})

    @staticmethod
    def server_rebuild(view, request, kwargs):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        image_id = data.get('image_id', '')
        server_id = kwargs.get(view.lookup_field)
        try:
            server = ServerManager().get_manage_perm_server(
                server_id=server_id, user=request.user, related_fields=['vo'])
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        if server.task_status == server.TASK_CREATE_FAILED:
            return view.exception_response(
                exceptions.ConflictError(message=_('创建失败的云主机不支持重建'))
            )
        if server.task_status == server.TASK_IN_CREATING:
            return view.exception_response(
                exceptions.ConflictError(message=_('正在创建中的云主机不支持重建'))
            )

        if server.is_locked_operation():
            return view.exception_response(exceptions.ResourceLocked(
                message=_('云主机已加锁锁定了任何操作，请解锁后重试')
            ))

        server.task_status = server.TASK_IN_CREATING
        server.image = ''
        server.image_id = image_id
        server.image_desc = ''
        server.default_user = ''
        server.raw_default_password = ''
        try:
            with transaction.atomic():
                server.save(update_fields=['task_status', 'image', 'image_id', 'image_desc',
                                           'default_user', 'default_password'])

                params = inputs.ServerRebuildInput(server_id=server.instance_id, image_id=image_id)
                try:
                    r = view.request_service(server.service, method='server_rebuild', params=params)
                except exceptions.APIException as exc:
                    raise exc

                if not r.ok:
                    raise r.error
        except Exception as exc:
            return view.exception_response(exc)

        update_fields = []
        admin_password = r.default_password
        if admin_password:
            server.raw_default_password = admin_password
            server.default_user = r.default_user if r.default_user else 'root'
            update_fields.append('default_user')
            update_fields.append('default_password')

        if server.instance_id != r.server_id:
            server.instance_id = r.server_id
            update_fields.append('instance_id')

        if update_fields:
            server.save(update_fields=update_fields)

        server_build_status.creat_task(server)  # 异步任务查询server创建结果，更新server信息和创建状态
        data = {
            'id': server.id,
            'image_id': r.image_id
        }
        return Response(data=data, status=202)


class ServerArchiveHandler:
    @staticmethod
    def list_archives(view, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        queryset = ServerArchiveManager().get_user_archives_queryset(
            user=request.user, service_id=service_id)

        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(queryset, request=request, view=view)
            serializer = serializers.ServerArchiveSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def list_vo_archives(view, request, kwargs):
        vo_id = kwargs.get('vo_id')
        service_id = request.query_params.get('service_id', None)

        vo_mgr = VoManager()
        vo = vo_mgr.get_vo_by_id(vo_id)
        if vo is None:
            raise exceptions.NotFound(message=_('项目组不存在'))

        try:
            vo_mgr.check_read_perm(vo=vo, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        queryset = ServerArchiveManager().get_vo_archives_queryset(vo_id=vo_id, service_id=service_id)
        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(queryset, request, view=view)
            serializer = serializers.ServerArchiveSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

