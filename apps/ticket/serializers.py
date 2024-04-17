from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.ticket.models import Ticket


class TicketCreateSerializer(serializers.Serializer):
    title = serializers.CharField(
        label=_('标题'), min_length=10, max_length=250, required=True, help_text=_('疑问或问题的简述'))
    description = serializers.CharField(
        label=_('问题描述'), min_length=10, required=True, help_text=_('客户的疑问或问题的描述'),
    )
    service_type = serializers.CharField(
        label=_('工单相关服务'), max_length=16, required=True, help_text=f'{Ticket.ServiceType.choices}'
    )
    contact = serializers.CharField(
        label=_('联系方式'), max_length=128, required=False, allow_blank=True, default='', help_text=_('工单提交人联系方式'),
    )


class TicketSerializer(serializers.Serializer):
    id = serializers.CharField(label='id')
    title = serializers.CharField(label=_('标题'), max_length=250, help_text=_('疑问或问题的简述'))
    description = serializers.CharField(label=_('问题描述'))
    status = serializers.CharField(label=_('状态'), max_length=16)
    service_type = serializers.CharField(label=_('工单相关服务'), max_length=16)
    severity = serializers.CharField(label=_('严重程度'), max_length=16)
    submit_time = serializers.DateTimeField(label=_('提交时间'))
    modified_time = serializers.DateTimeField(label=_('修改时间'))
    contact = serializers.CharField(label=_('联系方式'), max_length=128)
    resolution = serializers.CharField(label=_('解决方案'))
    submitter = serializers.SerializerMethodField(label=_('工单提交人'), method_name='get_submitter')
    assigned_to = serializers.SerializerMethodField(label=_('分配给'), method_name='get_assigned_to')

    @staticmethod
    def get_submitter(obj):
        if obj.submitter:
            return {'id': obj.submitter.id, 'username': obj.submitter.username}

        return None

    @staticmethod
    def get_assigned_to(obj):
        if obj.assigned_to:
            return {'id': obj.assigned_to.id, 'username': obj.assigned_to.username}

        return None


class TicketWithRatingSerializer(TicketSerializer):
    rating = serializers.SerializerMethodField(label=_('工单评价'), method_name='get_ticket_rating')

    @staticmethod
    def get_ticket_rating(obj: Ticket):
        ticket_rating = getattr(obj, 'ticket_rating', None)
        if ticket_rating:
            return {'score': obj.ticket_rating.score}

        return None


class TicketChangeSerializer(serializers.Serializer):
    id = serializers.CharField(label='id')
    ticket_field = serializers.CharField(label=_('字段'))
    old_value = serializers.CharField(label=_('旧值'))
    new_value = serializers.CharField(label=_('新值'))


class FollowUpCreateSerializer(serializers.Serializer):
    comment = serializers.CharField(label=_('回复/评论'), required=True)


class FollowUpSerializer(serializers.Serializer):
    id = serializers.CharField(label='id')
    title = serializers.CharField(label=_('标题'), max_length=250, help_text=_('疑问或问题的简述'))
    comment = serializers.CharField(label=_('回复/评论'), required=True)
    submit_time = serializers.DateTimeField(label=_('提交时间'))
    fu_type = serializers.CharField(label=_('类型'))
    ticket_id = serializers.CharField(label=_('工单ID'))
    user = serializers.SerializerMethodField(label=_('提交人'), method_name='get_user')
    ticket_change = TicketChangeSerializer(required=False)

    @staticmethod
    def get_user(obj):
        if obj.user:
            return {'id': obj.user.id, 'username': obj.user.username}

        return None


class TicketRatingSerializer(serializers.Serializer):
    id = serializers.CharField(label='id', read_only=True)
    score = serializers.IntegerField(label=_('评分'), min_value=1, max_value=5, help_text=_('评分 1-5'))
    comment = serializers.CharField(label=_('评论'), max_length=1024, allow_blank=True, default='')

    ticket_id = serializers.CharField(label=_('工单编号'), read_only=True)
    submit_time = serializers.DateTimeField(label=_('提交时间'), read_only=True)
    modified_time = serializers.DateTimeField(label=_('修改时间'), read_only=True)
    user_id = serializers.CharField(label=_('评价提交人id'), read_only=True)
    username = serializers.CharField(label=_('提交人用户名'), read_only=True)
    is_sys_submit = serializers.BooleanField(label=_('系统默认提交'), read_only=True)
