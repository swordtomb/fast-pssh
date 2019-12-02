#!/usr/bin/python3
import subprocess
import fcntl
import threading

from fpslib.manager import Manager
from fpslib.task import Task
from fpslib.cli import base_parser


def parse_args():
    parser = base_parser()
    opts, args = parser.parse_args()

    return opts, args


def do_pssh():
    host_list = []

    manager = Manager()
    fit(manager, host_list)

    manager.run()


def fit(manager, host_list, remote_cmd):
    for host, user, port in host_list:
        cmd = gen_cmd(host, user, port, remote_cmd)

        task = Task(cmd)
        manager.add_task(task)


def gen_cmd(host, user, port, remote_cmd):
    cmd = ['ssh', '-T', host]
    cmd += ['-l', user]
    cmd += ['-p', port]
    cmd.append(remote_cmd)
    return cmd


if __name__ == '__main__':
    pass
