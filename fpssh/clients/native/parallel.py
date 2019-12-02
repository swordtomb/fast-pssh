from fpssh.clients.base_parallel import BaseParallelSSHClient
from gevent.lock import RLock
from fpssh.clients.native.single import SSHClient


class ParallelSSHClient(BaseParallelSSHClient):

    def __init__(self, hosts, user, password, port):
        BaseParallelSSHClient.__init__(self, hosts, user, password, port)
        self._clients_lock = RLock()

    def _run_command(self, host, command):
        self._make_ssh_client(host)
        return self.host_clients[host].run_command(command)

    def _make_ssh_client(self, host):
        # TODO 搞懂锁
        with self._clients_lock:
            self.host_clients[host] = SSHClient(host, self.user, self.password, self.port)


if "__main__" == __name__:
    fake_cmd = "echo foo"
    fake_res = "foo\n"
    hosts = ["127.0.0.1", "127.0.0.1"]
    port = 2222
    user = "foo"
    password = "foo"
    client = ParallelSSHClient(hosts, user, password, port)

    def test_run_command():
        outputs = client.run_command(fake_cmd)
        for host, output in outputs.items():
            print(host, list(output[0]))


    test_run_command()