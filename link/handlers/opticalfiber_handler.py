from django.utils.translation import gettext as _
from api.viewsets import NormalGenericViewSet
from link.managers.userrole_manager import UserRoleWrapper
from link.managers.opticalfiber_manager import OpticalFiberManager
from core import errors
from link.utils.verify_utils import VerifyUtils

class OpticalFiberHandler:
    def list_opticalfiber(view: NormalGenericViewSet, request):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        try:
            params = OpticalFiberHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)
        queryset = OpticalFiberManager.filter_queryset(
            is_linked=params['is_linked']
            ).order_by('fiber_cable', 'sequence')
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    def _list_validate_params(request):
        is_linked = request.query_params.get('is_linked', None)

        if is_linked is not None:
            is_linked = VerifyUtils.string_to_bool(is_linked)
            if is_linked is None:
                raise errors.InvalidArgument(message=_('参数“is_linked”是无效的布尔类型'))
        return {
            'is_linked': is_linked
        }

