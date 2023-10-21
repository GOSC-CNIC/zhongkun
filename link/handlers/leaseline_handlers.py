from django.utils.translation import gettext as _

from core import errors
from api.viewsets import NormalGenericViewSet
from datetime import date
from link.managers.userrole_managers import UserRoleWrapper
from link.managers.leaseline_managers import LeaseLineManager
from core import errors
from api.handlers.handlers import serializer_error_msg
from rest_framework.response import Response
from link.serializers.leaseline_serializers import LeaseLineSerializer

class LeaseLineHandler:

    def creat_leaseline(self, view: NormalGenericViewSet, request):
        try:
            data = self._create_validate_params(view=view, request=request)
        except Exception as exc:
            return view.exception_response(exc)
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_write_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的编辑权限')))
        leaseline = LeaseLineManager.create_leaseline(
            private_line_number=data['private_line_number'],
            lease_line_code=data['lease_line_code'],
            line_username=data['line_username'],
            endpoint_a=data['endpoint_a'],
            endpoint_z=data['endpoint_z'],
            line_type=data['line_type'],
            cable_type=data['cable_type'],
            bandwidth=data['bandwidth'],
            length=data['length'],
            provider=data['provider'],
            enable_date=data['enable_date'],
            is_whithdrawal=data['is_whithdrawal'],
            money=data['money'],
            remarks=data['remarks']
        )
        return Response(data=LeaseLineSerializer(instance=leaseline).data)

    def _create_validate_params(self, view: NormalGenericViewSet, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise errors.BadRequest(message=msg)

        data = serializer.validated_data
        return data
    

    def list_leaseline(self, view: NormalGenericViewSet, request):
        try:
            params = self._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        queryset = LeaseLineManager().get_queryset(
            is_whithdrawal=params['is_whithdrawal'], search=params['search'], enable_date_start=params['enable_date_start'], enable_date_end=params['enable_date_end']
        )
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        is_whithdrawal = request.query_params.get('is_whithdrawal', None)
        search = request.query_params.get('search', None)
        enable_date_start = request.query_params.get('enable_date_start', None)
        enable_date_end = request.query_params.get('enable_date_end', None)

        if is_whithdrawal:
            is_whithdrawal = is_whithdrawal.lower()
            if is_whithdrawal == 'true':
                is_whithdrawal = True
            elif is_whithdrawal == 'false':
                is_whithdrawal = False
            else:
                raise errors.InvalidArgument(message=_('参数“is_whithdrawal”是无效的布尔类型'))

        if enable_date_start:
            try:
                enable_date_start = date.fromisoformat(enable_date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“enable_date_start”是无效的日期格式'))

        if enable_date_end:
            try:
                enable_date_end = date.fromisoformat(enable_date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“enable_date_start”是无效的日期格式'))

        return {
            'is_whithdrawal': is_whithdrawal,
            'search': search,
            'enable_date_start': enable_date_start,
            'enable_date_end':  enable_date_end
        }
