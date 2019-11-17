import os
import select
import threading
import queue
from enum import Enum


class Manager:
    def __init__(self):
        self.limit = 2
        self.outdir = None
        self.tasks = []
        self.running = []
        self.done = []
        self.wlist = {}
        self.queue = queue.Queue()

    def run(self):
        # 有输出路径拉起线程写数据
        if self.outdir:
            writer = Writer()
            writer.start()

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
            task.run()


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
