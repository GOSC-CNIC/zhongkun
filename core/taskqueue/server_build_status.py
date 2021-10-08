import time
from concurrent.futures import ThreadPoolExecutor

from core import request


_pool_executor = ThreadPoolExecutor()


def creat_task(server):
    try:
        _pool_executor.submit(task_server_build_status, server)
    except Exception as e:
        return False

    return True


def task_server_build_status(server):
    """
    尝试更新服务器的详细信息
    :param server:
    :return:
        True    # success
        False   # failed
    """
    marker = 0
    failed_count = 0
    while True:
        r = request.server_build_status(server)
        if r == 'failed':      # 创建失败
            server.refresh_from_db()
            if server.task_status == server.TASK_IN_CREATING:
                failed_count += 1
                if failed_count >= 3:
                    server.task_status = server.TASK_CREATE_FAILED
                    server.save(update_fields=['task_status'])
                    return

        elif r == 'created':
            break
        elif r == 'error':
            marker += 1
            if marker > 10:     # 多次查询失败，放弃
                break
        else:
            failed_count = 0

        time.sleep(1)

    marker = 0
    while True:
        try:
            if request.update_server_detail(server):
                break
        except Exception as e:
            marker += 1
            if marker > 3:  # 多次更新失败，放弃
                break

        time.sleep(1)
