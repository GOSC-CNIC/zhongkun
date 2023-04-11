from .server_build_status import _pool_executor


def submit_task(task, kwargs: dict = None):
    try:
        return _pool_executor.submit(task, **kwargs)
    except Exception as e:
        return None
