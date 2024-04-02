from django.utils.translation import gettext as _
from rest_framework.response import Response
from rest_framework.serializers import DecimalField

from vo.managers import VoManager, VoMemberManager, VoMember
from vo import vo_serializers
from utils.model import OwnerType
from core import errors as exceptions
from api.viewsets import CustomGenericViewSet, serializer_error_msg
from servers.managers import ServerManager, DiskManager
from order.managers import OrderManager
from apps.app_wallet.models import CashCoupon
from apps.app_wallet.managers import PaymentManager


class VoHandler:
    @staticmethod
    def list_vo(view: CustomGenericViewSet, request, kwargs):
        _owner = request.query_params.get('owner', None)
        _member = request.query_params.get('member', None)
        _name = request.query_params.get('name', None)

        if _owner is not None:
            _owner = True
        if _member is not None:
            _member = True

        try:
            if view.is_as_admin_request(request=request):
                queryset = VoManager().get_admin_vo_queryset(
                    user=request.user, owner=_owner, member=_member, name=_name
                )
            else:
                queryset = VoManager().get_user_vo_queryset(
                    user=request.user, owner=_owner, member=_member, name=_name
                )

            paginator = view.pagination_class()
            vos = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = view.get_serializer(instance=vos, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create(view, request, kwargs):
        """
        创建一个组
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        name = data.get('name')
        company = data.get('company')
        description = data.get('description')

        try:
            vo = VoManager().create_vo(name=name, company=company, description=description, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=view.get_serializer(instance=vo).data)

    @staticmethod
    def delete_vo(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        try:
            VoManager().delete_vo(vo_id=vo_id, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        return Response(status=204)

    @staticmethod
    def update_vo(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        name = data.get('name')
        company = data.get('company')
        description = data.get('description')

        try:
            vo = VoManager().update_vo(vo_id=vo_id, admin_user=request.user, name=name,
                                       company=company, description=description)
            return Response(data=vo_serializers.VoSerializer(instance=vo).data)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def vo_add_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data.get('usernames', [])
        try:
            success_members, failed_usernames = VoManager().add_members(
                vo_id=vo_id, usernames=usernames, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        members = vo_serializers.VoMemberSerializer(success_members, many=True).data
        return Response(data={'success': members, 'failed': failed_usernames})

    @staticmethod
    def vo_list_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        try:
            vo, members = VoManager().get_vo_members_queryset(vo_id=vo_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        data = view.get_serializer(members, many=True).data
        return Response(data={
            'members': data, 'owner': {'id': vo.owner.id, 'username': vo.owner.username}})

    @staticmethod
    def vo_remove_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data.get('usernames', [])
        try:
            VoManager().remove_members(vo_id=vo_id, usernames=usernames, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        return Response(status=204)

    @staticmethod
    def vo_members_role(view, request, kwargs):
        member_id = kwargs.get('member_id')
        role = kwargs.get('role')
        if not role:
            raise exceptions.BadRequest(message=_('"role"的值无效'))

        try:
            member = VoMemberManager().change_member_role(
                member_id=member_id, role=role, admin_user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data=vo_serializers.VoMemberSerializer(member).data)

    @staticmethod
    def vo_statistic(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        user = request.user
        try:
            vo, member = VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
            vo_member_qs = VoMemberManager().get_vo_members_queryset(vo_id=vo_id)
            vo_member_count = vo_member_qs.count() + 1

            # 组角色
            if vo.owner_id == user.id:
                my_vo_role = 'owner'
            else:
                vmb = VoMember.objects.filter(vo_id=vo_id, user_id=user.id).first()
                my_vo_role = vmb.role

            vo_servers = ServerManager().get_vo_servers_queryset(vo_id=vo_id)
            vo_servers_count = vo_servers.count()

            vo_orders = OrderManager().filter_order_queryset(
                vo_id=vo_id, resource_type='', order_type='', status='', time_start=None, time_end=None)
            vo_orders_count = vo_orders.count()

            coupons_qs = CashCoupon.objects.filter(
                vo_id=vo_id, owner_type=OwnerType.VO.value,
                status=CashCoupon.Status.AVAILABLE.value
            )
            vo_coupons_count = coupons_qs.count()

            vo_balance = PaymentManager().get_vo_point_account(vo_id=vo_id)
            vo_disk_qs = DiskManager().get_vo_disks_queryset(vo_id=vo_id)
            vo_disk_count = vo_disk_qs.count()
            data = {
                'vo': {'id': vo.id, 'name': vo.name},
                'my_role': my_vo_role,
                'member_count': vo_member_count,
                'server_count': vo_servers_count,
                'disk_count': vo_disk_count,
                'order_count': vo_orders_count,
                'coupon_count': vo_coupons_count,
                'balance': DecimalField(max_digits=10, decimal_places=2).to_representation(vo_balance.balance)
            }
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=data)

    @staticmethod
    def devolve_vo_owner(view, request, kwargs):
        vo_id = kwargs['id']
        member_id = request.query_params.get('member_id')
        username = request.query_params.get('username')

        if not member_id and not username:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('必须指定组员id或者用户名')))
        elif member_id and username:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('不能同时指定组员id和用户名')))

        try:
            if member_id:
                vo = VoManager().devolve_vo_owner_to_member(
                    vo_id=vo_id, member_id=member_id, owner=request.user)
            elif username:
                vo = VoManager().devolve_vo_owner_to_username(
                    vo_id=vo_id, username=username, owner=request.user)
            else:
                raise exceptions.InvalidArgument(message=_('必须指定组员id或者用户名'))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data=vo_serializers.VoSerializer(vo).data)
