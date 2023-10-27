from django.utils.translation import gettext as _
from api.viewsets import NormalGenericViewSet
from datetime import date
from link.managers.userrole_manager import UserRoleWrapper
from link.managers.fibercable_manager import FiberCableManager
from core import errors
from api.handlers.handlers import serializer_error_msg
from rest_framework.response import Response
from link.serializers.fibercable_serializer import FiberCableSerializer
from link.utils.verify_utils import VerifyUtils

class FiberCableHandler:
    @staticmethod
    def creat_fibercable(view: NormalGenericViewSet, request):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_write_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的编辑权限')))
        try:
            data = FiberCableHandler._create_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)
        fibercable = FiberCableManager.create_fibercable(
            number=data['number'],
            fiber_count=data['fiber_count'],
            length=data['length'],
            endpoint_1=data['endpoint_1'],
            endpoint_2=data['endpoint_2'],
            remarks=data['remarks']
        )
        return Response(data=FiberCableSerializer(instance=fibercable).data)
    
    @staticmethod
    def _create_validate_params(view: NormalGenericViewSet, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise errors.BadRequest(message=msg)

        data = serializer.validated_data
        return data
    
    @staticmethod
    def list_fibercable(view: NormalGenericViewSet, request):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        try:
            params = FiberCableHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)
        queryset = FiberCableManager.filter_queryset(search=params['search'])
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        search = request.query_params.get('search', None)

        if VerifyUtils.is_blank_string(search):
            search = None

        return {
            'search': search
        }
