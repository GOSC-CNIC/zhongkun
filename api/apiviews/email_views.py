from django.utils.translation import gettext_lazy, gettext as _
from django.core.validators import EmailValidator, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema

from api.serializers import email as eamil_serializers
from api.viewsets import serializer_error_msg
from utils.paginators import NoPaginatorInspector
from utils.iprestrict import IPRestrictor, load_allowed_ips
from core import errors
from users.models import Email


class EmailIPRestrictor(IPRestrictor):
    SETTING_KEY_NAME = 'API_EMAIL_ALLOWED_IPS'
    _allowed_ip_rules = load_allowed_ips(SETTING_KEY_NAME)

    def reload_ip_rules(self):
        self.allowed_ips = load_allowed_ips(self.SETTING_KEY_NAME)


class EmailViewSet(viewsets.GenericViewSet):

    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[^/]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询自己的ip地址'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='realip', url_name='realip')
    def real_ip(self, request, *args, **kwargs):
        """
        查询自己的ip地址

            {
              "real_ip": "1227.0.0.1",
            }
        """
        ipv4, proxys = EmailIPRestrictor.get_remote_ip(request)
        return Response(data={
            'real_ip': ipv4,
            # 'proxys': proxys
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('提交发送邮件'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        提交发送邮件

            http code 200：
            {
                'id': '0726a0ca-0699-11ee-b56b-c8009fe2ebbc',
                'subject': 'test测试',
                'receiver': 'test@cnic.com;test66@cnic.com;test888@qq.com',
                'message': 'test测试',
                'is_html': false,
                'status': 'success', # wait 待发送; success 发送成功; failed 发送失败
                'status_desc': '',
                'success_time': '2023-06-09T07:41:21.482813Z',
                'remote_ip': '127.0.0.1',
                'is_feint': false   # true(假动作，只入库不真的发送)；false(入库并真的发送)
            }
        """
        try:
            data = self._create_validate_params(request=request)
        except Exception as exc:
            return self.exception_response(exc)

        try:
            remote_ip = EmailIPRestrictor().check_restricted(request=request)
        except errors.Error as exc:
            return self.exception_response(exc)

        is_html = data['is_html']
        if is_html:
            message = ''
            html_message = data['message']
        else:
            message = data['message']
            html_message = None

        email = Email.send_email(
            subject=data['subject'], receivers=data['receiver'],
            message=message, html_message=html_message,
            tag=Email.Tag.API.value, fail_silently=True,
            save_db=True, remote_ip=remote_ip, is_feint=data['is_feint']
        )
        serializer = eamil_serializers.EmailSerializer(instance=email)
        return Response(data=serializer.data)

    def _create_validate_params(self, request):
        """
        :raises: Error
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'subject' in s_errors:
                exc = errors.BadRequest(message=_('无效邮件标题。') + s_errors['subject'][0], code='InvalidSubject')
            elif 'receiver' in s_errors:
                exc = errors.BadRequest(
                    message=_('无效的邮件接收人。') + s_errors['receiver'][0], code='InvalidReceiver')
            elif 'message' in s_errors:
                exc = errors.BadRequest(
                    message=_('无效的邮件内容。') + s_errors['message'][0], code='InvalidMessage')
            elif 'is_html' in s_errors:
                exc = errors.BadRequest(
                    message=_('无效的邮件内容格式。') + s_errors['is_html'][0], code='InvalidIsHtml')
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data
        receiver_str = data['receiver']
        emails = receiver_str.split(';')
        receivers = []
        for m in emails:
            m = m.strip(' ')
            if not m:
                continue
            try:
                EmailValidator()(m)
            except ValidationError as exc:
                raise errors.BadRequest(message=_('邮箱地址无效。') + m, code='InvalidReceivers')

            receivers.append(m)

        if len(receivers) == 0:
            raise errors.BadRequest(message=_('邮箱地址无效。'), code='InvalidReceivers')

        data['receiver'] = receivers
        return data

    def get_serializer_class(self):
        if self.action in ['create', ]:
            return eamil_serializers.EmailSerializer

        return Serializer

    @staticmethod
    def exception_response(exc):
        if isinstance(exc, errors.Error):
            return Response(data=exc.err_data(), status=exc.status_code)

        exc = errors.Error(message=str(exc))
        return Response(data=exc.err_data(), status=exc.status_code)

    def get_permissions(self):
        if self.action == 'create':
            return []

        return super().get_permissions()
