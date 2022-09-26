from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ticket.models import Ticket


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
        label=_('联系方式'), max_length=128, required=False, default='', help_text=_('工单提交人联系方式'),
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
