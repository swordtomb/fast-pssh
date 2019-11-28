import logging
import paramiko
from gevent import monkey
monkey.patch_all()


class SSHClient:

    def __init__(self):
        client = paramiko.SSHClient()
        self.client = client
        self.host = None
        self.port = None