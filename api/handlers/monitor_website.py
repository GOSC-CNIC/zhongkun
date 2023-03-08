import time

from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from monitor.managers import MonitorWebsiteManager, WebsiteQueryChoices
from monitor.models import MonitorWebsiteTask, MonitorWebsiteVersionProvider, MonitorWebsite, WebsiteDetectionPoint
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
            user = request.user
            if not user.is_federal_admin():
                count = MonitorWebsite.objects.filter(user_id=user.id).count()
                if count >= 2:
                    raise errors.ConflictError(message=_('已达到允许创建监控任务数量上限。'), code='TooManyTask')

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

    @staticmethod
    def change_website_task(view: CustomGenericViewSet, request, kwargs):
        """
        修改站点监控信息任务
        """
        website_id = kwargs.get(view.lookup_field)
        try:
            params = MonitorWebsiteHandler._create_website_validate_params(view=view, request=request)
            task = MonitorWebsiteManager.change_website_task(
                _id=website_id,
                name=params['name'],
                url=params['url'],
                remark=params['remark'],
                user=request.user
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        data = view.get_serializer(instance=task).data
        return Response(data=data)

    @staticmethod
    def list_website_task(view: CustomGenericViewSet, request):
        """
        列举用户站点监控任务
        """
        try:
            queryset = MonitorWebsiteManager.get_user_website_queryset(user_id=request.user.id)
            websites = view.paginate_queryset(queryset=queryset)
        except Exception as exc:
            return view.exception_response(exc)

        data = view.get_serializer(instance=websites, many=True).data
        return view.get_paginated_response(data=data)

    @staticmethod
    def delete_website_task(view: CustomGenericViewSet, request, kwargs):
        """
        删除用户站点监控任务
        """
        try:
            website_id = kwargs.get(view.lookup_field)
            MonitorWebsiteManager.delete_website_task(_id=website_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def get_website_task_version(view: CustomGenericViewSet, request):
        ins = MonitorWebsiteVersionProvider.get_instance()
        return Response(data={'version': ins.version})

    @staticmethod
    def monitor_list_website_task(view: CustomGenericViewSet, request):
        """
        拉取站点监控任务
        """
        try:
            queryset = MonitorWebsiteTask.objects.all()
            tasks = view.paginate_queryset(queryset=queryset)
        except Exception as exc:
            return view.exception_response(exc)

        data = view.get_serializer(instance=tasks, many=True).data
        return view.get_paginated_response(data=data)

    @staticmethod
    def query_monitor_data(view: CustomGenericViewSet, request, kwargs):
        """
        查询站点的监控数据
        """
        website_id = kwargs.get(view.lookup_field)
        query = request.query_params.get('query', None)

        if query is None:
            return view.exception_response(errors.BadRequest(message=_('参数"query"是必须提交的')))

        if query not in WebsiteQueryChoices.values:
            return view.exception_response(errors.InvalidArgument(message=_('参数"query"的值无效')))

        mgr = MonitorWebsiteManager()
        try:
            website = mgr.get_user_website(website_id=website_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = mgr.query(website=website, tag=query)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)

    @staticmethod
    def query_range_monitor_data(view: CustomGenericViewSet, request, kwargs):
        """
        查询站点的监控数据
        """
        website_id = kwargs.get(view.lookup_field)

        mgr = MonitorWebsiteManager()
        try:
            query, start, end, step = MonitorWebsiteHandler.validate_query_range_params(request)
            website = mgr.get_user_website(website_id=website_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = mgr.query_range(website=website, tag=query, start=start, end=end, step=step)
        except errors.Error as exc:
            return view.exception_response(exc)
        
        return Response(data=data, status=200)

    @staticmethod
    def validate_query_range_params(request):
        """
        :return:
            (service_id: str, query: str, start: int, end: int, step: int)

        :raises: Error
        """
        query = request.query_params.get('query', None)
        start = request.query_params.get('start', None)
        end = request.query_params.get('end', int(time.time()))
        step = request.query_params.get('step', 300)

        if query is None:
            raise errors.BadRequest(message=_('参数"query"是必须提交的'))

        if query not in WebsiteQueryChoices.values:
            raise errors.InvalidArgument(message=_('参数"query"的值无效'))

        if start is None:
            raise errors.BadRequest(message=_('参数"start"必须提交'))

        try:
            start = int(start)
            if start <= 0:
                raise ValueError
        except ValueError:
            raise errors.InvalidArgument(message=_('起始时间"start"的值无效, 请尝试一个正整数'))

        try:
            end = int(end)
            if end <= 0:
                raise ValueError
        except ValueError:
            raise errors.InvalidArgument(message=_('截止时间"end"的值无效, 请尝试一个正整数'))

        timestamp_delta = end - start
        if timestamp_delta < 0:
            raise errors.BadRequest(message=_('截止时间必须大于起始时间'))

        try:
            step = int(step)
        except ValueError:
            raise errors.InvalidArgument(message=_('步长"step"的值无效, 请尝试一个正整数'))

        if step <= 0:
            raise errors.InvalidArgument(message=_('不接受零或负查询解析步长, 请尝试一个正整数'))

        resolution = timestamp_delta // step
        if resolution > 10000:
            raise errors.BadRequest(message=_('超过了每个时间序列10000点的最大分辨率。尝试降低查询分辨率（？step=XX）'))

        return query, start, end, step

    @staticmethod
    def list_website_detection_point(view: CustomGenericViewSet, request):
        """
        列举站点监控探测点
        """
        enable = request.query_params.get('enable', None)
        if isinstance(enable, str):
            enable = enable.lower()
            if enable == 'true':
                enable = True
            elif enable == 'false':
                enable = False
            else:
                return view.exception_response(errors.InvalidArgument('参数“enable”的值无效。'))

        queryset = WebsiteDetectionPoint.objects.all()
        if enable is not None:
            queryset = WebsiteDetectionPoint.objects.filter(enable=enable)

        try:
            points = view.paginate_queryset(queryset=queryset)
        except Exception as exc:
            return view.exception_response(exc)

        data = view.get_serializer(instance=points, many=True).data
        return view.get_paginated_response(data=data)
