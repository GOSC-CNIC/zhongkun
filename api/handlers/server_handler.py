from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors as exceptions
from service.managers import ServiceManager
from servers.models import Server
from servers.managers import ServerManager, ServerArchiveManager
from api import paginations
from api.viewsets import CustomGenericViewSet
from api import serializers
from vo.managers import VoManager


class ServerHandler:
    @staticmethod
    def list_servers(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        user_id = request.query_params.get('user-id')
        vo_id = request.query_params.get('vo-id')

        if user_id and vo_id:
            return view.exception_response(exceptions.BadRequest(
                message=_('参数“user-id”和“vo-id”不能同时提交')))

        if view.is_as_admin_request(request):
            try:
                servers = ServerManager().get_admin_servers_queryset(
                    user=request.user, service_id=service_id, user_id=user_id, vo_id=vo_id)
            except Exception as exc:
                return view.exception_response(exceptions.convert_to_error(exc))
        else:
            if user_id or vo_id:
                return view.exception_response(exceptions.BadRequest(
                    message=_('参数“user-id”和“vo-id”只能和参数“as-admin”一起提交')))

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

