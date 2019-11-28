import logging
import os

from ssh2.session import Session
from gevent import socket

from ...exceptions import SessionError, UnknownHostException, ConnectionErrorException, PKeyFileError
from ssh2.error_codes import LIBSSH2_ERROR_EAGAIN
from socket import gaierror as sock_gaierror, error as sock_error


class SSHClient:
    def __init__(self):
        self.session = Session()
        self.sock = None
        self.pkey = None

    def __del__(self):
        self.session.disconnect()

    def __exit__(self):
        self.session.disconnect()

    def _connect(self, host, port, retries=1):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((host, port))
        except sock_gaierror as ex:
            raise UnknownHostException(ex)

        except sock_error as ex:
            raise ConnectionErrorException(ex)

    def open_session(self):
        try:
            chan = self.session.open_session()
        except Exception as ex:
            raise SessionError(ex)

        return chan

    def run_command(self, command):
        channel = self.open_session()
        channel.execute(command)
        return self.read_output_buffer(channel.read), self.read_output_buffer(channel.read_stderr)

    def auth(self):
        self.session.userauth_publickey_fromfile(self.user, self.pkey)

    def _pkey_path(self, pkey):
        pkey = os.path.expanduser(pkey)
        if os.path.exists(pkey):
            ex = PKeyFileError()
            raise ex
        return pkey

    def read_output_buffer(self, func):
        encoding = "utf-8"
        buffer = self._read_output(func)
        for line in buffer:
            output = line.decode(encoding)
            yield output

    def read_stderr(self, channel):
        return self._read_output(channel.read_stderr)

    def read_output(self, channel):
        return self._read_output(channel.read)

    @staticmethod
    def _read_output(func):
        buffer = ''
        size, data = func()
        while size > 0:
            buffer = buffer + data
            size, data = func()
        return buffer

    def disconnect(self):
        self.session.disconnect()
        self.sock.close()