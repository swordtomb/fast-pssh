#!/usr/bin/python3
import subprocess
import fcntl
import threading

from fpslib.manager import Manager
from fpslib.task import Task
from fpslib.cli import base_parser
from fpssh.clients.native.parallel import ParallelSSHClient


def parse_args():
    parser = base_parser()
    args = parser.parse_args()
    return args


def do_pssh():
    host_list = []

    manager = Manager()
    fit(manager, host_list)

    manager.run()


def do_fpssh(cmd):
    hosts = ["tail1"]
    user = "root"
    password = "456"
    client = ParallelSSHClient(hosts, user, password, 22)
    return client.run_command(cmd)


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
    args = parse_args()


    #do_pssh()
    outputs = do_fpssh(args.cmd)
    for host, output in outputs.items():
        print(host, list(output[0]))
