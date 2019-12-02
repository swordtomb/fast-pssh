from gevent import pool


class BaseParallelSSHClient:

    def __init__(self, hosts, user, password, port):
        self.pool_size = 4
        self.pool = pool.Pool(self.pool_size)
        self.hosts = hosts
        self.user = user
        self.password = password
        self.port = port
        self.pkey = None
        self.host_clients = {}

    def run_command(self, command):
        output = {}
        cmds = [self.pool.spawn(self._run_command, host, command) for host in self.hosts]
        for cmd in cmds:
            stdout, stderr, host = cmd.get()
            output[host] = (stdout, stderr)

        return output

    def _run_command(self, host, command):
        raise NotImplementedError

