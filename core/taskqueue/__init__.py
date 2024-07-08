import functools
from typing import Union
from concurrent.futures import ThreadPoolExecutor, Future

from django.db import connections


_thread_pool_executor = ThreadPoolExecutor()


def before_close_old_connections(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for conn in connections.all(initialized_only=True):
            conn.close_if_unusable_or_obsolete()

        return func(*args, **kwargs)

    return wrapper


def submit_task(task, kwargs: dict = None) -> Union[Future, None]:
    task = before_close_old_connections(task)
    try:
        return _thread_pool_executor.submit(task, **kwargs)
    except Exception as e:
        return None
