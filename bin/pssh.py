#!/usr/bin/python3
import subprocess

from lib.manager import Manager
from lib.task import Task
from lib.cli import base_parser

import threading


class FooThread(threading.Thread):

    def run(self):
        print('exec job\n')

t1 = FooThread()
t2 = FooThread()
t1.start()
t2.start()


def parse_args():
    parser = base_parser()
    opts, args = parser.parse_args()

    return opts, args


def do_pssh():
    host = ''
    cmd = ['ssh', '-T', host]

    manager = Manager()
    task = Task()
    manager.add_task(task)

    subprocess.run(cmd)

if __name__ == '__main__':

    pass
