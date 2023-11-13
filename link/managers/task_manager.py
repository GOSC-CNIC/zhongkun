from django.utils.translation import gettext as _
from link.models import Task
from core import errors
from django.db import transaction

class TaskManager:
    @staticmethod
    def get_queryset():
        return Task.objects.all()

    @staticmethod
    def get_normal_queryset():
        return TaskManager.get_queryset().exclude(task_status=Task.TaskStatus.DELETED)

    @staticmethod
    def get_task(id: str):
        """
        :raises: TaskNotExist
        """
        task = TaskManager.get_queryset().filter(id=id).first()
        if task is None:
            raise errors.TargetNotExist(message=_('业务不存在'), code='TaskNotExist')
        return task

    @staticmethod
    def create_task(
            number: str,
            user: str,
            endpoint_a: str,
            endpoint_z: str,
            bandwidth: float,
            task_description: str,
            line_type: str,
            task_person: str,
            build_person: str,
            task_status: str,
    ) -> Task:
        with transaction.atomic():
            task = Task(
                number=number,
                user=user,
                endpoint_a=endpoint_a,
                endpoint_z=endpoint_z,
                bandwidth=bandwidth,
                task_description=task_description,
                line_type=line_type,
                task_person=task_person,
                build_person=build_person,
                task_status=task_status
            )
            task.save(force_insert=True)
        return task

    @staticmethod
    def filter_queryset(task_status: list = None):
        qs = TaskManager.get_queryset()

        if task_status is not None:
            qs = qs.filter(task_status__in=task_status)

        return qs
