import logging
import os

from ssh2.session import Session
from gevent import socket, get_hub

from ...exceptions import SessionError, UnknownHostException, ConnectionErrorException, PKeyFileError, \
    AuthenticationException
from ssh2.error_codes import LIBSSH2_ERROR_EAGAIN
from socket import gaierror as sock_gaierror, error as sock_error

THREAD_POOL = get_hub().threadpool


class SSHClient:
    def __init__(self, host, user, password, port=22):
        self.session = None
        self.sock = None
        self.pkey = None
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.keepalive_seconds = 60
        self._connect(self.host, self.port)
        self._init()

        _auth_thread_pool = True

    def __del__(self):
        self.disconnect()

    def __exit__(self):
        self.disconnect()

    def _connect(self, host, port, retries=1):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((host, port))
        except sock_gaierror as ex:
            raise UnknownHostException(ex)

        except sock_error as ex:
            raise ConnectionErrorException(ex)

    def _init(self):
        self.session = Session()
        self.session.handshake(self.sock)
        self.auth()

    def open_session(self):
        try:
            chan = self.session.open_session()
        except Exception as ex:
            raise SessionError(ex)

        return chan

    def run_command(self, command):
        channel = self.open_session()
        channel.execute(command)
        return self.read_output_buffer(channel.read), self.read_output_buffer(channel.read_stderr), self.host

    def auth(self):
        self._password_auth()
        # self.session.userauth_publickey_fromfile(self.user, self.pkey)

    def _pkey_path(self, pkey):
        pkey = os.path.expanduser(pkey)
        if os.path.exists(pkey):
            ex = PKeyFileError()
            raise ex
        return pkey

    def _password_auth(self):
        try:
            self.session.userauth_password(self.user, self.password)
        except Exception:
            raise AuthenticationException("Password authentication failed")

    def read_output_buffer(self, func):
        buffer = self._read_output(func)
        for line in buffer:
            yield line

    def read_stderr(self, channel):
        return self._read_output(channel.read_stderr)

    def read_stdout(self, channel):
        return self._read_output(channel.read)

    @staticmethod
    def _read_output(func):
        encoding = "utf-8"
        buffer = []
        size, data = func()
        while size > 0:
            buffer.append(data.decode(encoding))
            size, data = func()
        return buffer

    def disconnect(self):
        self.session.disconnect()
        self.sock.close()