from django.utils.translation import gettext as _
from api.viewsets import NormalGenericViewSet
from link.managers.userrole_manager import UserRoleWrapper
from link.managers.element_manager import ElementManager
from link.managers.leaseline_manager import LeaseLineManager
from link.managers.connectorbox_manager import ConnectorBoxManager
from link.managers.opticalfiber_manager import OpticalFiberManager
from link.managers.distriframeport_manager import DistriFramePortManager
from rest_framework.response import Response
from core import errors
from link.models import Element
from link.utils.verify_utils import VerifyUtils
from link.serializers.element_data_serializer import ElementDataSerializer
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
            element = ElementManager.get_element_by_id(id=id)
            data['type'] = Element.get_api_type(element.object_type)
            if element.object_type == Element.Type.LEASE_LINE:
                data['lease'] = LeaseLineManager.get_leaseline(id=element.object_id)
            elif element.object_type == Element.Type.OPTICAL_FIBER:
                data['fiber'] = OpticalFiberManager.get_opticalfiber(id=element.object_id)
            elif element.object_type == Element.Type.DISTRIFRAME_PORT:
                data['port'] = DistriFramePortManager.get_distriframeport(id=element.object_id)
            elif element.object_type == Element.Type.CONNECTOR_BOX:
                data['box'] = ConnectorBoxManager.get_connectorbox(id=element.object_id)
        except errors.Error as exc:
            return view.exception_response(exc)
        return Response(data=ElementDataSerializer(instance=data).data)
