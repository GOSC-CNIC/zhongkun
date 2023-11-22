from django.utils.translation import gettext as _
from api.viewsets import NormalGenericViewSet
from link.managers.userrole_manager import UserRoleWrapper
from link.managers.element_manager import ElementManager
from rest_framework.response import Response
from core import errors
from link.models import Element
from link.utils.verify_utils import VerifyUtils
from link.serializers.link_serializer import ElementDetailDataSerializer
class ElementHandler:
    @staticmethod
    def retrieve_element(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        id = kwargs[view.lookup_field]
        if VerifyUtils.is_blank_string(id):
            return view.exception_response(errors.InvalidArgument(message=_('无效id')))
        data = {
            'type': None,
            'lease': None,
            'fiber': None,
            'port': None,
            'box': None
        }
        try:
            data = ElementManager.get_element_detail_data_by_id(id)
        except errors.Error as exc:
            return view.exception_response(exc)
        return Response(data=ElementDetailDataSerializer(instance=data).data)
