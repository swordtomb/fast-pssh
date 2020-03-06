from errno import EINTR

import fcntl
import os
import threading
import queue
import select
import sys
import signal
from enum import Enum, unique
from fpslib.askpass_server import PasswordServer

READ_SIZE = 1 << 16


class Manager:
    def __init__(self, opts):
        self.limit = opts.par
        self.timeout = opts.timeout

        self.outdir = opts.outdir
        self.errdir = opts.errdir
        self.iomap = make_iomap()

        # self.next_nodenum = 0
        # self.numnodes = 0
        self.current_node_num = 0
        self.node_count = 0
        self.tasks = []
        self.running = []
        self.done = []

        self.wlist = {}
        self.queue = queue.Queue()





        # TODO Ask Pass
        self.askpass = ""

    def run(self):
        try:
            # 有输出路径拉起线程写数据
            if self.outdir or self.errdir:
                writer = Writer()
                writer.start()
            else:
                writer = None

            if self.askpass:
                pass_server = PasswordServer()

            self.set_sigchld_handler()

            try:
                self.update_task(writer)
                wait = None
                while self.running or self.tasks:
                    if wait is None or wait < 1:
                        wait = 1
                    self.iomap.poll(wait)
                    self.update_task(writer)
                    wait = self.check_timeout()

            except KeyboardInterrupt:
                #
                self.interrupt_clean()

        except KeyboardInterrupt:
            # 不打印错误信息直接先后走，结束程序
            pass

        if writer:
            writer.signal_quit()
            writer.join()

        return [task.exit_code for task in self.done]

    def add_task(self, task):
        self.tasks.append(task)
        self.node_count += 1

    def update_task(self, writer):
        """收集完成的Task，启动下一批"""
        # Mask signal Python Bug
        # http://bugs.python.org/issue1068268
        # 因为sigprocmask 不在 stdlib，所以调用
        # 因为信号是masked，所以要每次调用reap_tasks()
        running = True
        while running:
            self.clear_sigchld_handler()
            self._start_tasks_once(writer)
            self.set_sigchld_handler()
            running = self.reap_tasks()

    def clear_sigchld_handler(self):
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    def set_sigchld_handler(self):
        signal.signal(signal.SIGCHLD, self.handle_sigchld)
        # EINTR
        if hasattr(signal, "siginterrupt"):
            signal.siginterrupt(signal.SIGCHLD, False)

    def handle_sigchld(self, num, frame):
        """sigchld 信号的处理函数"""
        # poll()底层调用waitpid(pid, WNOHANG)，清理僵尸进程。
        # 这样捕捉SIGCHLD处理僵尸进程是个标准套路。
        # 子进程调用exit()后不会立即消失而是留下僵尸进程，父进程调用wait或waitpid。子进程才消失。
        # 但是这一步不取返回值，在Manager.run()循环中再次调用poll取返回值。
        for task in self.running:
            if task.proc:
                # 设置进程返回码s
                task.proc.poll()
        # 一些 UNIX系统会重置 SIGCHLD handler 为 SIG_DFL所以得再设置一次
        self.set_sigchld_handler()

    def reap_tasks(self):

        still_running = []
        finished_count = 0
        for task in self.running:
            if task.is_running():
                still_running.append(task)
            else:
                self.finished(task)
                finished_count += 1
        self.running = still_running

        return finished_count

    def interrupt_clean(self):
        """keyboard中断后，清理"""
        for task in self.running:
            task.interrupted()
            self.finished(task)

        for task in self.running:
            task.cancel()
            self.finished(task)

    def finished(self, task):
        self.done.append(task)
        n = len(self.done)
        task.report(n)

    def _start_tasks(self):
        for task in self.tasks:
            self.running.append(task)
            task.start()

    def _start_tasks_once(self, writer):
        while 0 < len(self.tasks) and len(self.running) <= self.limit:
            task = self.tasks.pop(0)
            self.running.append(task)
            task.start(self.current_node_num, self.node_count, self.iomap, writer)
            self.current_node_num += 1

    def check_timeout(self):
        """杀死超时进程，返回最小剩余时间"""
        if self.timeout <= 0:
            return None
        min_timeleft = None
        for task in self.running:
            timeleft = self.timeout - task.elapsed()
            if timeleft <= 0:
                task.timedout()
            elif min_timeleft is None or timeleft < min_timeleft:
                min_timeleft = timeleft
        if min_timeleft is None:
            return 0
        else:
            return max(0, min_timeleft)


class IOMap:

    def __init__(self):
        self.readmap = {}
        self.writemap = {}

        # 设置 唤醒时激发的文件描述符，防止进程挂起收不到信号
        readfd, writefd = os.pipe()
        self.register_read(readfd, self.wakeup_handler)

        # 文件描述符没数据也直接返回不会阻塞等待数据
        fcntl.fcntl(writefd, fcntl.F_SETFL, os.O_NONBLOCK)
        # 信号到达，将信号值写入文件描述符，用于唤醒主线程
        # set_wakeup_fd只能在主线程调用
        signal.set_wakeup_fd(writefd)

    def register_read(self, fd, handler):
        self.readmap[fd] = handler

    def register_write(self, fd, handler):
        self.writemap[fd] = handler

    def unregister(self, fd):
        if fd in self.readmap:
            del self.readmap[fd]
        if fd in self.writemap:
            del self.writemap[fd]

    def poll(self, timeout=None):
        if not self.readmap and not self.writemap:
            return
        rlist = list(self.readmap)
        wlist = list(self.writemap)

        try:
            # 没有I/O事件，会阻塞在这。
            rlist, wlist, _ = select.select(rlist, wlist, [], timeout)
        except select.error:
            _, e, _ = sys.exc_info()
            errno = e.args[0]
            if errno == EINTR:
                return
            else:
                raise

        for fd in rlist:
            handler = self.readmap[fd]
            handler(fd, self)
        for fd in wlist:
            handler = self.writemap[fd]
            handler(fd, self)

    def wakeup_handler(self, fd, iomap):
        """
        :param fd:
        :param iomap:
        :return:
        确保 SIGCHLD 信号不会丢失
        子进程结束会向父进程发送 SIGCHLD信号
        """
        try:
            os.read(fd, READ_SIZE)
        except (OSError, IOError):
            _, e, _ = sys.exc_info()
            errno, msg = e.args
            if errno != EINTR:
                sys.stderr.write(
                    f"Fatal error in reading from wakeup iomap pipe: {msg}\n")
            raise FatalError


class PollIOMap(IOMap):

    def __init__(self):
        self._poller = select.poll()
        super(PollIOMap, self).__init__()

    def register_read(self, fd, handler):
        super(PollIOMap, self).register_read(fd, handler)
        self._poller.register(fd, select.POLLIN)

    def register_write(self, fd, handler):
        super(PollIOMap, self).register_write(fd, handler)
        self._poller.register(fd, select.POLLOUT)

    def unregister(self, fd):
        super(PollIOMap, self).unregister(fd)
        self._poller.unregister(fd)

    def poll(self, timeout=None):
        if not self.readmap and not self.writemap:
            return
        try:
            event_list = self._poller.poll(timeout)
        except select.error:
            _, e, _ = sys.exc_info()
            errno = e.args[0]
            if errno == EINTR:
                return
            else:
                raise
        for fd, event in event_list:
            if event & (select.POLLIN | select.POLLHUP):
                handler = self.readmap[fd]
                handler(fd, self)
            if event & (select.POLLOUT | select.POLLERR):
                handler = self.writemap[fd]
                handler(fd, self)


class EpollIOMap:
    pass


def make_iomap():
    if hasattr(select, 'poll'):
        return PollIOMap()
    else:
        return IOMap()


@unique
class Sig(Enum):
    EOF = -1
    OPEN = 0
    KILL = 1
    WRITE = 2


class Writer(threading.Thread):
    def __init__(self, out_dir):
        super().__init__()
        self.queue = queue.Queue()
        self.out_dir = out_dir

    def run(self):
        while True:
            sig, file, data = self.queue.get()
            if sig == Sig.KILL:
                return
            # if 没有直接打开文件，懒加载
            if sig == Sig.OPEN:
                self.files[file] = None
            if sig == Sig.EOF and self.files[file] is not None:
                self.files[file].close()
            if sig == Sig.WRITE:
                if self.files[file] is None:
                    self.files[file] = open(file, 'wb', buffering=1)
                self.files[file].write(data)
                self.files[file].flush()

    def open_files(self, file):
        self.queue.put(Sig.OPEN, file, None)

    def write(self, file, data):
        self.queue.put(Sig.WRITE, file, data)

    def close(self, file):
        self.queue.put(Sig.EOF, file, None)

    def quit(self):
        self.queue.put((Sig.KILL, None, None))


class FatalError(RuntimeError):
    """A fatal error in the PSSH Manager."""
    pass