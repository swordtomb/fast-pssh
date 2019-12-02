import unittest
from fpssh.clients.native.parallel import ParallelSSHClient


class ParallelSSHClientTest(unittest.TestCase):

    def setUp(self):
        self.fake_cmd = "echo foo"
        self.fake_res = "foo\n"
        self.hosts = ["127.0.0.1", "127.0.0.1"]
        self.port = 2222
        self.user = "foo"
        self.password = "foo"
        self.client = ParallelSSHClient()

    def test_run_command(self):
        outputs = self.client.run_command(self.fake_cmd)
        for host, output in outputs.items():
            print(host, output[0])