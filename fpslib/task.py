import os
from subprocess import Popen, PIPE
import signal
import time

BUFFER_SIZE = 1 << 16

class Task:

    def __init__(self, host, cmd=None, stdin=None):
        self.host = host
        self.cmd = cmd
        self.proc = None
        self.timestamp = None
        self.killed = False
        self.failures = []

        self.inputbuffer = stdin

        self.stdin = None
        self.stdout = None
        self.stderr = None

        self.outfile = None

    def start(self, iomap, writer):
        env = os.environ.copy()

        self.proc = Popen(self.cmd, stdin=PIPE, stderr=PIPE, stdout=PIPE)
        self.timestamp = time.time()

        if self.inputbuffer:
            self.stdin = self.proc.stdin
            iomap.register_write(self.stdin.fileno(), self.handle_stdin)
        else:
            self.proc.stdin.close()

        self.stdout = self.proc.stdout
        iomap.register_read(self.stdout.fileno(), self.handle_stdout)
        self.stderr = self.proc.stderr
        iomap.register_read(self.stderr.fileno(), self.handle_stderr)

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

    def handle_stdin(self, fd, iomap):
        pass

    def handle_stdout(self, fd, iomap):
        try:
            buf = os.read(fd, BUFFER_SIZE)
            if buf:
                if self.outfile:
                    self
        except:
            pass

    def handle_stderr(self, fd, iomap):
        pass


if __name__ == '__main__':
    cmd = ['ls', '-l']
    task = Task(cmd)
    task.run()
