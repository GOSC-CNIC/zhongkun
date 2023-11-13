from django.utils.translation import gettext as _
from api.viewsets import NormalGenericViewSet
from link.managers.userrole_manager import UserRoleWrapper
from link.managers.elementlink_manager import ElementLinkManager
from core import errors
from link.utils.verify_utils import VerifyUtils
from link.models import ElementLink
from rest_framework.response import Response
from link.serializers.elementlink_serializer import ElementLinkSerializer
class ElementLinkHandler:
    @staticmethod
    def list_elementlink(view: NormalGenericViewSet, request):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        try:
            params = ElementLinkHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)
        queryset = ElementLinkManager.filter_queryset(
            task_id=params['task_id'], link_status=params['link_status']
            )
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        task_id = request.query_params.get('task_id', None)
        link_status = request.query_params.getlist('link_status', [])
        if VerifyUtils.is_blank_string(task_id):
            task_id = None
        link_status_set = set(link_status)
        for status in link_status_set:
            if VerifyUtils.is_blank_string(status) or status not in list(map(str, ElementLink.LinkStatus)):
                raise errors.InvalidArgument(message=_(f'参数“link_status”链路状态无效, val:{status}'))
        if VerifyUtils.is_empty_list(link_status_set):
            link_status_set=None

        return {
            'task_id': task_id,
            'link_status': link_status_set,
        }

    @staticmethod
    def retrieve_elementlink(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        id = kwargs[view.lookup_field]
        if VerifyUtils.is_blank_string(id):
            return view.exception_response(errors.InvalidArgument(message=_('无效id')))
        try:
            elementlink = ElementLinkManager.get_elementlink(id=id)
        except errors.Error as exc:
            return view.exception_response(exc)
        return Response(data=ElementLinkSerializer(instance=elementlink).data)
