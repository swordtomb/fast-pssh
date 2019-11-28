import fcntl
import re

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


def set_cloexec(filelike):
    # 有可能有问题
    fcntl.fcntl(filelike.fileno(), fcntl.FD_CLOEXEC, 1)

if __name__ == '__main__':
    parser = HostParser()
    path = ''
    parser.read_host_file(path)
