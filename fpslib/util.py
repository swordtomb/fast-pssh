import fcntl
import re
import fnmatch
import sys

DEFAULT_USER = "root"
DEFAULT_PORT = "22"


class HostParser:

    def __init__(self):
        self.user = DEFAULT_USER
        self.port = DEFAULT_PORT
        self.host = []

    def read_host_file(self, path):
        lines = []
        with open(path, 'r') as f:
            for line in f:
                lines.append(line.strip())

        for line in lines:
            line.strip()
            self.host.append(self._parse_line(line))

        return self.host

    def _parse_line(self, line):
        host = line
        user = self.user
        port = self.port

        if '@' in line:
            user, addr = line.split('@')
        if ':' in addr:
            host, port = addr.rsplit(':')

        return host, port, user


def read_host_files(paths, host_glob, default_user=None, default_port=None):
    """
    :param paths:
    :param host_glob:
    :param default_user:
    :param default_port:
    :return: a list of (host, port, user) triples
    """
    hosts = []
    if paths:
        for path in paths:
            hosts.extend(read_host_file(path, host_glob, default_user=default_user))
    return hosts


def read_host_file(path, host_glob, default_user=None, default_port=None):
    lines = []
    with open(path, 'r') as f:
        for line in f:
            lines.append(line.strip())
    hosts = []
    for line in lines:
        # 删除注释
        line = re.sub("#.*", '', line)
        line.strip()

        # 删除空行
        if line:
            host, port, user = parse_host_entry(line, default_user, default_port)
            # glob 通配符判断
            if host and (not host_glob or fnmatch.fnmatch(host, host_glob)):
                hosts.append((host, port, user))

    return hosts


# [user@][host][:port]
def parse_host_entry(line, default_user, default_port):

    fields = line.split()
    if len(fields) > 2:
        sys.stderr.write(f"Bad line {line}. Format should be "
                         "[user@][host][:port] [user]\n")
        return None, None, None
    host_field = fields[0]
    host, user, port = parse_host(host_field, default_port=default_port)

    if len(fields) == 2:
        if user is None:
            user = fields[1]
        else:
            sys.stderr.write(f'User specified twice in line: {line}\n' % line)
            return None, None, None

    if user is None:
        user = default_user
    return host, user, port


# 解析命令行传入的主机信息
def parse_host_string(host_string, default_user=None, default_port=None):
    hosts = []
    entries = host_string.split()
    for entry in entries:
        hosts.append(parse_host(entry, default_user, default_port))
    return hosts


def parse_host(host, default_user=None, default_port=None):
    user = default_user
    port = default_port

    if '@' in host:
        user, host = host.split('@', 1)
    if ':' in host:
        host, port = host.rsplit(':', 1)

    return host, port, user


def set_cloexec(filelike):
    # exec 调用时自动关闭文件描述符
    # 所有文件描述符都设置了这个，subprocess.Popen()可以不设置close_fds
    fcntl.fcntl(filelike.fileno(), fcntl.FD_CLOEXEC, 1)


if __name__ == '__main__':
    parser = HostParser()
    path = ''
    parser.read_host_file(path)
