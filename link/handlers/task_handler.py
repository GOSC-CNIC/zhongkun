from django.utils.translation import gettext as _
from api.viewsets import NormalGenericViewSet
from link.managers.userrole_manager import UserRoleWrapper
from link.managers.task_manager import TaskManager
from core import errors
from link.utils.verify_utils import VerifyUtils
from link.models import Task
from rest_framework.response import Response
from link.serializers.task_serializer import TaskSerializer
class TaskHandler:
    @staticmethod
    def list_task(view: NormalGenericViewSet, request):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        try:
            params = TaskHandler._list_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)
        queryset = TaskManager.filter_queryset(task_status=params['task_status'])
        try:
            datas = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=datas, many=True)
            return view.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_validate_params(request):
        task_status = request.query_params.getlist('task_status', [])
        task_status_set = set(task_status)
        for status in task_status_set:
            if VerifyUtils.is_blank_string(status) or status not in list(map(str, Task.TaskStatus)):
                raise errors.InvalidArgument(message=_(f'参数“task_status”业务状态无效, val:{status}'))
        if VerifyUtils.is_empty_list(task_status_set):
            task_status_set = None

        return {
            'task_status': task_status_set,
        }

    @staticmethod
    def retrieve_task(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_read_permission():
            return view.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的可读权限')))
        id = kwargs[view.lookup_field]
        if VerifyUtils.is_blank_string(id):
            return view.exception_response(errors.InvalidArgument(message=_('无效id')))
        try:
            task = TaskManager.get_task(id=id)
        except errors.Error as exc:
            return view.exception_response(exc)
        return Response(data=TaskSerializer(instance=task).data)
