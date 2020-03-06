import errno
import getpass
import textwrap
import tempfile
import os
import socket
import sys
from fpslib import util


class PasswordServer:

    def __init__(self):
        self.sock = None
        self.tempdir = None
        self.address = None
        self.socketmap = {}
        self.buffermap = {}

    def start(self, iomap, backlog):

        msg = ("Warning: don't enter your password if anyone else "
               "has superuser privileges or access to account.")
        # 自动调整换行符，默认70字符加一个换行
        print(textwrap.fill(msg))
        # 命令行获取密码
        self.password = getpass.getpass()

        # mkdtemp只被创建的用户拥有读写权限
        self.tempdir = tempfile.mkdtemp(prefix="pssh.")
        self.address = os.path.join(self.tempdir, "pssh_askpass_socket")
        # 本地IPC 通信
        self.sock = socket.socket(socket.AF_UNIX)

        util.set_cloexec(self.sock)
        self.sock.bind(self.address)
        self.sock.listen(backlog)
        iomap.register_read(self.sock.fileno, self.handle_listen)

    def handle_listen(self, fd, iomap):
        try:
            conn = self.sock.accept()[0]
        except socket.error:
            _, e, _ = sys.exc_info()
            number = e.args[0]
            if number == errno.EINTR:
                return
            else:
                # TODO: print a error msg
                self.sock.close()
                self.sock = None
        fd = conn.fileno()
        iomap.register_write()
        self.socketmap[fd] = conn
        self.buffermap[fd] = self.password

    def handle_write(self, fd, iomap):
        buffer = self.buffermap[fd]
        conn = self.socketmap[fd]
        try:
            bytes_written = conn.send(buffer.encode())
        except socket.error:
            _, e, _ = sys.exc_info()
            number = e.args[0]
            if number == errno.EINTR:
                return
            else:
                self.close_socket(fd, iomap)
        # 把发送出去的字节从buffer中清掉
        buffer = buffer[bytes_written:]
        if buffer:
            self.buffermap[fd] = buffer
        else:
            self.close_socket(fd, iomap)

    def close_socket(self, fd, iomap):
        iomap.unregister(fd)
        self.socketmap[fd].close()
        del self.socketmap[fd]
        del self.buffermap[fd]

    def __del__(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        if self.address:
            os.remove(self.address)
        if self.tempdir:
            os.rmdir(self.tempdir)