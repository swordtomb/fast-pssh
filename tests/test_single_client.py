import unittest
from fpssh.clients.native.single import SSHClient


class SSHClientTest(unittest.TestCase):

    def setUp(self):
        self.fake_cmd = "echo foo"
        self.fake_res = "foo\n"
        self.host = "127.0.0.1"
        self.port = 2222
        self.user = "foo"
        self.password = "foo"
        self.client = SSHClient(self.host, self.user, self.password, self.port)

    def test_execute(self):
        stdout, stderr = self.client.run_command(self.fake_cmd)

        out = list(stdout)

        self.assertEqual([self.fake_res], out)


if "__main__" == __name__:
    unittest.main(verbosity=2)
