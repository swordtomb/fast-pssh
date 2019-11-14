import logging
import paramiko


class SSHClient:

    def __init__(self):
        client = paramiko.SSHClient()
        self.client = client