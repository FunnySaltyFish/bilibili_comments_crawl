"""
asyncio 协程介绍:
    - 动态添加任务：
        - 方案是创建一个线程，使事件循环在线程内永久运行
        - 设置守护进程，随着主进程一起关闭
    - 自动停止任务
    - 阻塞任务完成
    - 协程池
        - asyncio.Semaphore() 进行控制
https://blog.csdn.net/weixin_43968923/article/details/111397237
"""

import asyncio
import aiohttp
import time
import queue
from threading import Thread


class AsyncPool(object):
    """
    1. 支持动态添加任务
    2. 支持自动停止事件循环
    3. 支持最大协程数
    """

    def __init__(self, maxsize=1, loop=None):
        """
        初始化
        :param loop:
        :param maxsize: 默认为1
        """
        # 在jupyter需要这个，不然asyncio运行出错
        # import nest_asyncio
        # nest_asyncio.apply()

        # 队列，先进先出，根据队列是否为空判断，退出协程
        self.task = queue.Queue()

        # 协程池
        self.loop, _ = self.start_loop(loop)
        # 限制并发量为500
        self.semaphore = asyncio.Semaphore(maxsize)

    def task_add(self, item=1):
        """
        添加任务
        :param item:
        :return:
        """
        self.task.put(item)

    def task_done(self, fn):
        """
        任务完成
        回调函数
        :param fn:
        :return:
        """
        if fn:
            pass
        self.task.get()
        self.task.task_done()

    def wait(self):
        """
        等待任务执行完毕
        :return:
        """
        self.task.join()

    @property
    def running(self):
        """
        获取当前线程数
        :return:
        """
        return self.task.qsize()

    @staticmethod
    def _start_thread_loop(loop):
        """
        运行事件循环
        :param loop: loop以参数的形式传递进来运行
        :return:
        """
        # 将当前上下文的事件循环设置为循环。
        asyncio.set_event_loop(loop)
        # 开始事件循环
        loop.run_forever()

    async def _stop_thread_loop(self, loop_time=1):
        """
        停止协程
        关闭线程
        :return:
        """
        while True:
            if self.task.empty():
                # 停止协程
                self.loop.stop()
                break
            await asyncio.sleep(loop_time)

    def start_loop(self, loop):
        """
        运行事件循环
        开启新线程
        :param loop: 协程
        :return:
        """
        # 获取一个事件循环
        if not loop:
            loop = asyncio.new_event_loop()

        loop_thread = Thread(target=self._start_thread_loop, args=(loop,))
        # 设置守护进程
        loop_thread.daemon = True
        # 运行线程，同时协程事件循环也会运行
        loop_thread.start()

        return loop, loop_thread

    def stop_loop(self, loop_time=1):
        """
        队列为空，则关闭线程
        :param loop_time:
        :return:
        """
        # 关闭线程任务
        asyncio.run_coroutine_threadsafe(self._stop_thread_loop(loop_time), self.loop)

    def release(self, loop_time=1):
        """
        释放线程
        :param loop_time:
        :return:
        """
        self.stop_loop(loop_time)

    async def async_semaphore_func(self, func):
        """
        信号包装
        :param func:
        :return:
        """
        async with self.semaphore:
            return await func

    def submit(self, func, callback=None):
        """
        提交任务到事件循环
        :param func: 异步函数对象
        :param callback: 回调函数
        :return:
        """
        self.task_add()

        # 将协程注册一个到运行在线程中的循环，thread_loop 会获得一个环任务
        # 注意：run_coroutine_threadsafe 这个方法只能用在运行在线程中的循环事件使用
        # future = asyncio.run_coroutine_threadsafe(func, self.loop)
        future = asyncio.run_coroutine_threadsafe(self.async_semaphore_func(func), self.loop)

        # 添加回调函数,添加顺序调用
        future.add_done_callback(callback)
        future.add_done_callback(self.task_done)


async def thread_example(i):
    # url = "http://127.0.0.1:8080/app04/async4?num={}".format(i)
    # async with aiohttp.ClientSession() as session:
    #     async with session.get(url) as res:
    #         # print(res.status)
    #         # print(res.content)
    #         return await res.text()
    await asyncio.sleep(1)
    print("finish excute task i: ", i)
    return "finish excute task i: {}".format(i)


def my_callback(future):
    result = future.result()
    print('返回值: ', result)


def main():
    # 任务组， 最大协程数
    pool = AsyncPool(maxsize=3)

    # 插入任务任务
    for i in range(100):
        pool.submit(thread_example(i), my_callback)

    print("等待子线程结束1...")
    # 停止事件循环
    pool.release()

    # 获取线程数
    # print(pool.running)
    print("等待子线程结束2...")
    # 等待
    pool.wait()

    print("等待子线程结束3...")


if __name__ == '__main__':
    start_time = time.time()
    main()
    end_time = time.time()
    print("run time: ", end_time - start_time)

