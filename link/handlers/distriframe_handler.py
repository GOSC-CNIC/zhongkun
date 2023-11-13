from django.utils.translation import gettext as _
from api.viewsets import NormalGenericViewSet
from link.managers.userrole_manager import UserRoleWrapper
from link.managers.distriframe_manager import DistriFrameManager
from core import errors
from link.utils.verify_utils import VerifyUtils
from rest_framework.response import Response
from link.serializers.distriframe_serializer import DistriFrameSerializer
class DistriFrameHandler:
    @staticmethod
    def list_distriframe(view: NormalGenericViewSet, request):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        try:
            params = DistriFrameHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)
        queryset = DistriFrameManager.get_queryset()
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)
    
    @staticmethod
    def _list_validate_params(request):
        pass

    @staticmethod
    def retrieve_distriframe(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        id = kwargs[view.lookup_field]
        if VerifyUtils.is_blank_string(id):
            return view.exception_response(errors.InvalidArgument(message=_('无效id')))
        try:
            distriframe = DistriFrameManager.get_distriframe(id=id)
        except errors.Error as exc:
            return view.exception_response(exc)
        return Response(data=DistriFrameSerializer(instance=distriframe).data)
