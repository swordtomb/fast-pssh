from errno import EINTR

import fcntl
import os
import select
import threading
import queue
import select
import sys
import signal
from enum import Enum

READ_SIZE = 1 << 16


class Manager:
    def __init__(self):
        self.limit = 2
        self.outdir = None
        self.tasks = []
        self.running = []
        self.done = []
        self.wlist = {}
        self.queue = queue.Queue()

        self.askpass = ""
        self.timeout = ""

        self.iomap = make_iomap()

    def run(self):
        # 有输出路径拉起线程写数据
        if self.outdir or self.errdir:
            writer = Writer()
            writer.start()
        else:
            writer = None

        for task in self.tasks:
            stdout = task.run()
            self.wlist[task.host] = stdout

        if writer:
            writer.signal_quit()
            writer.join()

    def add_task(self, task):
        self.tasks.append(task)

    def _start_tasks(self):
        for task in self.tasks:
            self.running.append(task)
            task.start()

    def check_timeout(self):
        for task in self.running:
            timeleft = self.timeout - task.elapsed()
            if timeleft <= 0:
                task.timedout()





class IOMap:

    def __init__(self):
        self.readmap = {}
        self.writemap = {}
        readfd, writefd = os.pipe()
        self.register_read(readfd, self.wakeup_handler)

        fcntl.fcntl(writefd, fcntl.F_SETFL, os.O_NONBLOCK)
        signal.set_wakeup_fd(writefd)

    def register_read(self, fd, handler):
        self.readmap[fd] = handler

    def register_write(self, fd, handler):
        self.writemap[fd] = handler

    def unregister(self, fd):
        if fd in self.readmap:
            del self.readmap[fd]
        if fd in self.writemap:
            del self.writemap

    def poll(self, timeout=None):
        if not self.readmap and not self.writemap:
            return
        rlist = list(self.readmap)
        wlist = list(self.writemap)

        try:
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
        try:
            os.read(fd, READ_SIZE)
        except (OSError, IOError):
            _, e, _ = sys.exc_info()
            errno, message = e.args
            raise


class PollIOMap(IOMap):

    def __init__(self):
        self._poller = select.poll()
        super(PollIOMap, self).__init__()

    def register_read(self, fd, handler):
        pass

    def register_write(self, fd, handler):
        pass

    def unregister(self, fd):
        pass

    def poll(self, timeout=None):
        pass


class EpollIOMap:
    pass


def make_iomap():
    if hasattr(select, 'poll'):
        return PollIOMap()
    else:
        return IOMap()


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
                    self.files[file] = open(file, 'w', buffering=1)
                self.files[file].write(data)
                self.files[file].flush()

    def open(self, file):
        self.queue.put(Sig.OPEN, file, None)

    def write(self, file, data):
        self.queue.put(Sig.WRITE, file, data)

    def close(self, file):
        self.queue.put(Sig.EOF, file, None)

    def quit(self):
        self.queue.put((Sig.KILL, None, None))
