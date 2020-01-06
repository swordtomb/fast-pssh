import os
import subprocess
import signal
import time


class Task:

    def __init__(self, host, cmd=None):
        self.host = host
        self.cmd = cmd
        self.proc = None
        self.timestamp = None
        self.killed = False
        self.failures = []

    def run(self):
        env = os.environ.copy()
        # 3.5版本以上用run
        cp = subprocess.run(self.cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        self.timestamp = time.time()
        return cp.stdout

    def elapsed(self):
        """Finds the time in seconds since the process was started."""
        return time.time() - self.timestamp

    def timedout(self):
        self._kill()
        self.failures.append("Time out")

    def _kill(self):

        if self.proc:
            try:
                os.kill(-self.proc.pid, signal.SIGKILL)
            except OSError:
                pass

    def log_exception(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        exc = ("Exception: %s, %s, %s" %
               (exc_type, exc_value, traceback.format_tb(exc_traceback)))
        self.failures.append(exc)


if __name__ == '__main__':
    cmd = ['ls', '-l']
    task = Task(cmd)
    task.run()
