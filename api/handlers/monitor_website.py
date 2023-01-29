from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from monitor.managers import MonitorJobServerManager, ServerQueryChoices, MonitorWebsiteManager
from monitor.models import MonitorJobServer
from api.viewsets import CustomGenericViewSet
from .handlers import serializer_error_msg


class MonitorWebsiteHandler:
    @staticmethod
    def create_website_task(view: CustomGenericViewSet, request):
        """
        创建一个站点监控任务
        """
        try:
            params = MonitorWebsiteHandler._create_website_validate_params(view=view, request=request)
            task = MonitorWebsiteManager.add_website_task(
                name=params['name'],
                url=params['url'],
                remark=params['remark'],
                user_id=request.user.id
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        data = view.get_serializer(instance=task).data
        return Response(data=data)

    @staticmethod
    def _create_website_validate_params(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'name' in s_errors:
                exc = errors.BadRequest(message=_('无效的监控任务名称。') + s_errors['name'][0])
            elif 'url' in s_errors:
                exc = errors.BadRequest(
                    message=_('无效的站点网址。') + s_errors['url'][0], code='InvalidUrl')
            elif 'remark' in s_errors:
                exc = errors.BadRequest(
                    message=_('问题相关的服务无效。') + s_errors['remark'][0])
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        return serializer.validated_data
