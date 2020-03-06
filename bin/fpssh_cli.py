#!/usr/bin/python3
import os
import sys

parent, bindir = os.path.split(
    os.path.dirname(
        os.path.abspath(sys.argv[0])
    )
)

from fpslib import util
from fpslib.manager import Manager, FatalError
from fpslib.task import Task
from fpslib.cli import common_parser, common_defaults
from fpssh.clients.native.parallel import ParallelSSHClient

_DEFAULT_TIMEOUT = 60


def option_args():
    parser = common_parser()
    # 显示执行命令后远程主机的标准输出和标准错误输出
    parser.add_argument("-i", "--inline", dest="inline", action="store_true",
                        help="inline aggregated output and error for each server")
    parser.add_argument("--inline-stdout", dest="inline_stdout", action="store_true",
                        help="inline standard output for each server")
    parser.add_argument("-I", "--send-input", dest="send_input", action="store_true",
                        help="read from standard input and send as input to ssh")
    parser.add_argument("-P", "--print", dest="print_out", action="store_true",
                        help="print output as we get it")

    parser.add_argument("-c", dest="cmd", action="store")
    return parser


def parse_args():
    parser = option_args()
    defaults = common_defaults(timeout=_DEFAULT_TIMEOUT)
    parser.set_defaults(**defaults)
    # 解析设置的参数，没设置的也存下来作为发送到远程主机的命令
    opts, args = parser.parse_known_args()
    return opts, args


def do_pssh(hosts, cmdline, opts):
    if opts.outdir and not os.path.exists(opts.outdir):
        os.makedirs(opts.outdir)
    if opts.errdir and not os.path.exists(opts.errdir):
        os.makedirs(opts.errdir)
    if opts.send_input:
        if hasattr(sys.stdin, "buffer"):
            stdin = sys.stdin.buffer.read()
        else:
            stdin = sys.stdin.read()
    else:
        stdin = None

    manager = Manager(opts)

    for host, port, user in hosts:
        cmd = [
            "ssh", "-T", host, "-o", "NumberOfPasswordPrompts=1",
            "-o", "SendEnv=PSSH_NODENUM", "-o", "SendEnv=PSSH_NUMNODES",
            "-o", "SendEnv=PSSH_HOST"
        ]
        if opts.options:
            for opt in opts.options:
                cmd += ["-o", opt]
        if user:
            cmd += ["-l", user]
        if port:
            cmd += ["-p", port]
        if opts.extra:
            cmd.extend(opts.extra)
        if cmdline:
            cmd.append(cmdline)
        t = Task(host, port, user, cmd, opts, stdin)
        manager.add_task(t)

    try:
        statuses = manager.run()
    except FatalError:
        sys.exit(1)

    if any(x < 0 for x in statuses if x):
        # 有任何被杀
        sys.exit(3)
    if any(x == 255 for x in statuses):
        sys.exit(4)
    if any(x != 0 for x in statuses):
        sys.exit(5)


def fit(manager, host_list, remote_cmd):
    for host, user, port in host_list:
        cmd = gen_cmd(host, user, port, remote_cmd)

        task = Task(cmd)
        manager.add_task(task)

def do_fpssh(cmd):
    hosts = ["tail1"]
    user = "root"
    password = "456"
    client = ParallelSSHClient(hosts, user, password, 22)
    return client.run_command(cmd)





def gen_cmd(host, user, port, remote_cmd):
    cmd = ["ssh", "-T", host]
    cmd += ["-l", user]
    cmd += ["-p", port]
    cmd.append(remote_cmd)
    return cmd


if __name__ == "__main__":
    opts, args = parse_args()
    cmdline = " ".join(args)

    try:
        hosts = util.read_host_files(opts.host_files, opts.host_glob,
                                     default_user=opts.user)
    except IOError:
        _, e, _ = sys.exc_info()
        sys.stderr.write('Could not open hosts file: %s\n' % e.strerror)
        sys.exit(1)

    if opts.host_strings:
        for x in opts.host_strings:
            hosts.extend(util.parse_host_string(x, default_user=opts.user))

    do_pssh(hosts, cmdline, opts)


