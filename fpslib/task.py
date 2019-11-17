import os
import subprocess


class Task:

    def __init__(self, host, cmd=None):
        self.host = host
        self.cmd = cmd
        self.proc = None

    def run(self):
        env = os.environ.copy()
        # 3.5版本以上用run
        cp = subprocess.run(self.cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        return cp.stdout


if __name__ == '__main__':
    cmd = ['ls', '-l']
    task = Task(cmd)
    task.run()
