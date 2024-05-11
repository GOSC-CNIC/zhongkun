from django.utils.translation import gettext as _

from core import errors as exceptions
from apps.api.viewsets import CustomGenericViewSet
from apps.vo.managers import VoManager
from apps.servers.managers import ServerSnapshotManager
from apps.servers import serializers


class SnapshotHandler:

    @staticmethod
    def list_server_snapshot(view: CustomGenericViewSet, request):
        """
        列举云主机快照
        """
        try:
            params = SnapshotHandler._list_snapshot_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        service_id = params['service_id']
        server_id = params['server_id']
        remark = params['remark']
        vo_id: str = params['vo_id']
        vo_name = params['vo_name']
        username = params['username']
        user_id = params['user_id']
        exclude_vo = params['exclude_vo']

        if view.is_as_admin_request(request):
            try:
                queryset = ServerSnapshotManager().get_admin_snapshot_queryset(
                    admin_user=request.user, service_id=service_id, server_id=server_id, remark=remark,
                    user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, exclude_vo=exclude_vo
                )
            except Exception as exc:
                return view.exception_response(exc)
        elif vo_id:
            try:
                VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
            except exceptions.Error as exc:
                return view.exception_response(exc)

            queryset = ServerSnapshotManager().get_vo_snapshot_queryset(
                vo_id=vo_id, service_id=service_id, server_id=server_id, remark=remark
            )
        else:
            queryset = ServerSnapshotManager().get_user_snapshot_queryset(
                user=request.user, service_id=service_id, server_id=server_id, remark=remark
            )

        try:
            snapshots = view.paginate_queryset(queryset)
            serializer = serializers.ServerSnapshotSerializer(instance=snapshots, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_snapshot_validate_params(view, request):
        service_id = request.query_params.get('service_id', None)
        server_id = request.query_params.get('server_id', None)
        remark = request.query_params.get('remark', None)
        vo_id = request.query_params.get('vo_id', None)
        # as-admin only
        vo_name = request.query_params.get('vo_name', None)
        username = request.query_params.get('username', None)
        user_id = request.query_params.get('user_id', None)
        exclude_vo = request.query_params.get('exclude_vo', None)

        if user_id is not None and username is not None:
            raise exceptions.BadRequest(
                message=_('参数“user_id”和“username”不允许同时提交')
            )

        if vo_id is not None and vo_name is not None:
            raise exceptions.BadRequest(
                message=_('参数“vo_id”和“vo_name”不允许同时提交')
            )

        if exclude_vo is not None:
            exclude_vo = True
            if vo_id is not None or vo_name is not None:
                raise exceptions.BadRequest(
                    message=_('参数"exclude_vo"不允许与参数“vo_id”和“vo_name”同时提交')
                )
        else:
            exclude_vo = False

        if not view.is_as_admin_request(request):
            if username is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"username"只有以管理员身份请求时有效'))
            if user_id is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"user_id"只有以管理员身份请求时有效'))
            if vo_name is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"vo_name"只有以管理员身份请求时有效'))
            if exclude_vo:
                raise exceptions.InvalidArgument(
                    message=_('参数"exclude_vo"只有以管理员身份请求时有效'))

        return {
            'service_id': service_id,
            'server_id': server_id,
            'remark': remark,
            'vo_id': vo_id,
            'vo_name': vo_name,
            'username': username,
            'user_id': user_id,
            'exclude_vo': exclude_vo
        }
