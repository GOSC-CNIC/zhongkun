from typing import Union
from concurrent.futures import ThreadPoolExecutor, Future


_thread_pool_executor = ThreadPoolExecutor()


def submit_task(task, kwargs: dict = None) -> Union[Future, None]:
    try:
        return _thread_pool_executor.submit(task, **kwargs)
    except Exception as e:
        return None
