import asyncio
import requests
import random
import threading
import time


event_loop = asyncio.get_event_loop()
server_update_queue = asyncio.Queue(maxsize=10)


class ServerUpdateTask:
    async def task_update(self, server_uuid, t):
        while True:
            # future1 = self.loop.run_in_executor(None, requests.get, 'http://www.baidu.com')
            # r = await future1
            await asyncio.sleep(t)
            print(f'request 百度 ok, sleep({t});server_uuid={server_uuid}')
            server_update_queue.task_done()
            return
            # if r.ok:
            #     print(f'request 百度 ok, sleep({t})')
            #     print(f'server_uuid={server_uuid}')
            #     self.server_update_queue.task_done()
            # else:
            #     print(f'request 百度 error, sleep({t})')

    async def run_async_tasks(self, q):
        while True:
            try:
                server_uuid = q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            else:
                print(f'消息队列长度：{q.qsize()}')
                print('Tasks count: ', len(asyncio.all_tasks()))
                task = event_loop.create_task(self.task_update(server_uuid, random.choice([13, 14, 25, 26, 37, 48])),
                                           name=f'task-{server_uuid}')
            await asyncio.sleep(1)

    def run(self):
        event_loop.run_until_complete(self.run_async_tasks(server_update_queue))
        # asyncio.run(self.run_async_tasks(server_update_queue))

    async def producer(self, interval=2):
        while True:
            for i in range(10):
                await server_update_queue.put(str(i))
                await asyncio.sleep(interval)

            return

    async def run_test(self):
        await asyncio.gather(self.run_async_tasks(server_update_queue), self.producer())


if __name__ == "__main__":
    def producer():
        while True:
            for i in range(10):
                print(f'producer={i}\n')
                try:
                    return server_update_queue.put_nowait(str(i))
                except asyncio.QueueFull:
                    print('QueueFull')

                time.sleep(2)

            break   # janus

    threading.Thread(target=producer).start()
    ServerUpdateTask().run()
    # event_loop.run_until_complete(ServerUpdateTask().run_test())
