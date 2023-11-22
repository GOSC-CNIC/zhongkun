from django.utils.translation import gettext as _
from api.viewsets import NormalGenericViewSet
from link.managers.userrole_manager import UserRoleWrapper
from link.managers.link_manager import LinkManager
from link.managers.element_manager import ElementManager
from link.serializers.link_serializer import LinkSerializer, LinkDetailSerializer, LinkElementSerializer
from core import errors
from link.utils.verify_utils import VerifyUtils
from link.models import Link, ElementLink
from rest_framework.response import Response
from api.handlers.handlers import serializer_error_msg

class LinkHandler:
    @staticmethod
    def list_link(view: NormalGenericViewSet, request):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
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
        link_status_set = set(link_status)
        for status in link_status_set:
            if VerifyUtils.is_blank_string(status) or status not in list(map(str, Link.LinkStatus)):
                raise errors.InvalidArgument(message=_(f'参数“link_status”业务状态无效, val:{status}'))
        if VerifyUtils.is_empty_list(link_status_set):
            link_status_set = None

        return {
            'link_status': link_status_set,
        }

    @staticmethod
    def retrieve_link(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        id = kwargs[view.lookup_field]
        if VerifyUtils.is_blank_string(id):
            return view.exception_response(errors.InvalidArgument(message=_('无效id')))
        try:
            link = LinkManager.get_link(id=id)
        except errors.Error as exc:
            return view.exception_response(exc)
        return Response(data=LinkDetailSerializer(instance=link).data)

    @staticmethod
    def creat_link(view: NormalGenericViewSet, request):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_write_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的编辑权限')))
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
        if VerifyUtils.is_blank_string(data['link_status']) or data['link_status'] not in list(map(str, Link.LinkStatus)):
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
