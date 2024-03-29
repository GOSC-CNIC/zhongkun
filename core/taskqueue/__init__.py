from typing import Union
from concurrent.futures import Future

from .server_build_status import _pool_executor


def submit_task(task, kwargs: dict = None) -> Union[Future, None]:
    try:
        return _pool_executor.submit(task, **kwargs)
    except Exception as e:
        return None
