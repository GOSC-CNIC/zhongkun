from datetime import date

from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from apps.api.viewsets import NormalGenericViewSet, serializer_error_msg
from apps.app_net_link.managers.common import NetLinkUserRoleWrapper
from apps.app_net_link.managers.link import (
    LinkManager, DistriFrameManager, DistriFramePortManager, ElementManager,
    FiberCableManager, LeaseLineManager, OpticalFiberManager, ConnectorBoxManager
)
from apps.app_net_link import serializers as link_serializers
from apps.app_net_link.models import Link
from apps.app_net_link.verify_utils import VerifyUtils


class LinkHandler:
    @staticmethod
    def list_link(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            params = LinkHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        queryset = LinkManager.filter_queryset(link_status=params['link_status'])
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        link_status = request.query_params.getlist('link_status', [])
        link_status_set = list(set(link_status))

        for status in link_status_set:
            if status not in Link.LinkStatus.values:
                raise errors.InvalidArgument(message=_(f'参数“link_status”业务状态无效, val:{status}'))

        return {
            'link_status': link_status_set if link_status_set else None,
        }

    @staticmethod
    def retrieve_link(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            link = LinkManager.get_link(link_id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=link_serializers.LinkDetailSerializer(instance=link).data)

    @staticmethod
    def creat_link(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_write_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的编辑权限')))

        try:
            data = LinkHandler._create_validate_params(view=view, request=request)
            LinkManager.is_valid_link_element(link_element=data['link_element'])
        except errors.Error as exc:
            return view.exception_response(exc)

        link = LinkManager.create_link(
            number=data['number'],
            user=data['user'],
            endpoint_a=data['endpoint_a'],
            endpoint_z=data['endpoint_z'],
            bandwidth=data['bandwidth'],
            description=data['description'],
            line_type=data['line_type'],
            business_person=data['business_person'],
            build_person=data['build_person'],
            link_status=data['link_status'],
            remarks=data['remarks'],
            enable_date=data['enable_date'],
            link_element=data['link_element'],
        )
        return Response(data={
            'link_id': link.id
        })

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

        # 校验链路状态参数
        if data['link_status'] not in Link.LinkStatus.values:
            raise errors.InvalidArgument(message=_(f'参数“link_status”链路状态无效, val:{data["link_status"]}'))
        
        if not VerifyUtils.is_empty_list(data['link_element']):
            # 校验link_element的index和subindex，要求index从1开始递增，subindex默认为1，若index相同，则subindex从1开始递增
            data['link_element'] = link_element = sorted(data['link_element'], key=lambda x: (x["index"], x['sub_index']))
            index = 1
            sub_index = 1
            id_list = []
            for e in link_element:
                id_list.append(e["element_id"])
                if e["index"] != index and e["index"] != index + 1:
                    raise errors.InvalidArgument(message=_(f'不符合要求的link_element参数：index, 网元信息:{e}'))
                if e["index"] == index + 1:
                    index = index + 1
                    sub_index = 1
                if e["sub_index"] != sub_index:
                    raise errors.InvalidArgument(message=_(f'不符合要求的link_element参数：sub_index, 网元信息:{e}'))
                sub_index = sub_index + 1
            # 校验link_element的element_id不重复
            if len(id_list) != len(set(id_list)):
                raise errors.InvalidArgument(message=_(f'link_element参数不允许存在重复的element_id'))
        
        return data


class DistriFrameHandler:
    @staticmethod
    def list_distriframe(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        queryset = DistriFrameManager.get_queryset()
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def retrieve_distriframe(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            distriframe = DistriFrameManager.get_distriframe(id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=link_serializers.DistriFrameSerializer(instance=distriframe).data)


class DistriFramePortHandler:
    @staticmethod
    def list_distriframeport(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            params = DistriFramePortHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        queryset = DistriFramePortManager.filter_queryset(
            is_linked=params['is_linked'], distribution_frame_id=params['distribution_frame_id']
            ).order_by('distribution_frame', 'row', 'col')

        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        is_linked = request.query_params.get('is_linked', None)
        distribution_frame_id = request.query_params.get('frame_id', None)

        if is_linked is not None:
            is_linked = VerifyUtils.string_to_bool(is_linked)
            if is_linked is None:
                raise errors.InvalidArgument(message=_('参数“is_linked”是无效的布尔类型'))

        if VerifyUtils.is_blank_string(distribution_frame_id):
            distribution_frame_id = None

        return {
            'is_linked': is_linked,
            'distribution_frame_id': distribution_frame_id
        }


class ElementHandler:
    @staticmethod
    def retrieve_element(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        id = kwargs[view.lookup_field]
        if VerifyUtils.is_blank_string(id):
            return view.exception_response(errors.InvalidArgument(message=_('无效id')))

        try:
            data = ElementManager.get_element_detail_data_by_id(id)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=link_serializers.ElementDetailDataSerializer(instance=data).data)


class FiberCableHandler:
    @staticmethod
    def creat_fibercable(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_write_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的编辑权限')))

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
        return Response(data=link_serializers.FiberCableSerializer(instance=fibercable).data)

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
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

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
    def _list_fibercable_validate_params(request):
        search = request.query_params.get('search', None)

        if VerifyUtils.is_blank_string(search):
            search = None

        return {
            'search': search
        }

    @staticmethod
    def list_opticalfiber(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            fibercable = FiberCableManager.get_fibercable(
                id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        queryset = FiberCableManager.get_opticalfiber_queryset(fibercable=fibercable)
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

    @staticmethod
    def retrieve_fibercable(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            fibercable = FiberCableManager.get_fibercable(id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=link_serializers.FiberCableSerializer(instance=fibercable).data)


class LeaseLineHandler:
    @staticmethod
    def creat_leaseline(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_write_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的编辑权限')))

        try:
            data = LeaseLineHandler._create_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

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
        return Response(data=link_serializers.LeaseLineSerializer(instance=leaseline).data)

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
    def update_leaseline(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_write_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的编辑权限')))

        try:
            data = LeaseLineHandler._create_validate_params(view=view, request=request)
            leaseline = LeaseLineManager.get_leaseline(id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        leaseline = LeaseLineManager.update_leaseline(
            leaseline=leaseline,
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
        return Response(data=link_serializers.LeaseLineSerializer(instance=leaseline).data)

    @staticmethod
    def list_leaseline(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            params = LeaseLineHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        queryset = LeaseLineManager.filter_queryset(
            is_linked=params['is_linked'], is_whithdrawal=params['is_whithdrawal'], search=params['search'],
            enable_date_start=params['enable_date_start'], enable_date_end=params['enable_date_end']
        )
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        is_linked = request.query_params.get('is_linked', None)
        is_whithdrawal = request.query_params.get('is_whithdrawal', None)
        search = request.query_params.get('search', None)
        enable_date_start = request.query_params.get('enable_date_start', None)
        enable_date_end = request.query_params.get('enable_date_end', None)

        if VerifyUtils.is_blank_string(search):
            search = None

        if is_linked is not None:
            is_linked = VerifyUtils.string_to_bool(is_linked)
            if is_linked is None:
                raise errors.InvalidArgument(message=_('参数“is_linked”是无效的布尔类型'))

        if is_whithdrawal is not None:
            is_whithdrawal = VerifyUtils.string_to_bool(is_whithdrawal)
            if is_whithdrawal is None:
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

        if enable_date_start is not None and enable_date_end is not None:
            if enable_date_start > enable_date_end:
                raise errors.InvalidArgument(message=_('enable_date_start不能大于enable_date_end'))

        return {
            'is_linked': is_linked,
            'is_whithdrawal': is_whithdrawal,
            'search': search,
            'enable_date_start': enable_date_start,
            'enable_date_end': enable_date_end
        }

    @staticmethod
    def retrieve_leaseline(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            leaseline = LeaseLineManager.get_leaseline(id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=link_serializers.LeaseLineSerializer(instance=leaseline).data)


class OpticalFiberHandler:
    @staticmethod
    def list_opticalfiber(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            params = OpticalFiberHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        queryset = OpticalFiberManager.filter_queryset(
            is_linked=params['is_linked'], fiber_cable_id=params['fiber_cable_id']
            ).order_by('fiber_cable', 'sequence')
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        is_linked = request.query_params.get('is_linked', None)
        fiber_cable_id = request.query_params.get('cable_id', None)

        if is_linked is not None:
            is_linked = VerifyUtils.string_to_bool(is_linked)
            if is_linked is None:
                raise errors.InvalidArgument(message=_('参数“is_linked”是无效的布尔类型'))

        if VerifyUtils.is_blank_string(fiber_cable_id):
            fiber_cable_id = None

        return {
            'is_linked': is_linked,
            'fiber_cable_id': fiber_cable_id
        }


class ConnectorBoxHandler:
    @staticmethod
    def list_connectorbox(view: NormalGenericViewSet, request):
        ur_wrapper = NetLinkUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_link_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有链路管理功能的可读权限')))

        try:
            params = ConnectorBoxHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        queryset = ConnectorBoxManager.filter_queryset(is_linked=params['is_linked'])
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        is_linked = request.query_params.get('is_linked', None)

        if is_linked is not None:
            is_linked = VerifyUtils.string_to_bool(is_linked)
            if is_linked is None:
                raise errors.InvalidArgument(message=_('参数“is_linked”是无效的布尔类型'))

        return {
            'is_linked': is_linked
        }
