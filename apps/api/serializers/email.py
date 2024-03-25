from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class EmailSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=254, required=True, label=_('标题'))
    receiver = serializers.CharField(
        label=_('接收者'), max_length=254, required=True,
        help_text='邮件的接收人，如果是多个邮箱地址以英文“;”分隔，email1,email2,email3')
    message = serializers.CharField(label=_('邮件内容'), max_length=1000000, required=True)
    is_html = serializers.BooleanField(
        label='html格式信息', required=True,
        help_text='指示邮件内容是普通文本还是html格式信息，true指示为html格式信息')
    is_feint = serializers.BooleanField(
        label=_('是否是假动作，不真实发送'), allow_null=True, default=False,
        help_text='指示是否真实的发送邮件，true指示为假动作，只入库不真实发送邮件')

    id = serializers.CharField(label=_('邮件id'), read_only=True)
    status = serializers.CharField(label=_('发送状态'), max_length=16, read_only=True)
    status_desc = serializers.CharField(max_length=255, label=_('状态描述'), read_only=True)
    success_time = serializers.DateTimeField(label=_('成功发送时间'), read_only=True)
    remote_ip = serializers.CharField(max_length=64, label=_('客户端ip'), read_only=True)
