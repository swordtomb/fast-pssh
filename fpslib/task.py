import os
import sys
from subprocess import Popen, PIPE
import signal
import time
from errno import EINTR

from fpslib import color

BUFFER_SIZE = 1 << 16

class Task:

    def __init__(self, host, port, user, cmd, opts, stdin=None):
        # 退出状态码
        self.exit_code = None

        self.port = port
        self.host = host
        self.pertty_host = host
        self.cmd = cmd

        if user != opts.user:
            self.pertty_host = '@'.join((user, self.pertty_host))
        if port:
            self.pertty_host = ':'.join((self.pertty_host, port))

        self.proc = None
        self.writer = None
        self.timestamp = None
        self.killed = False
        self.failures = []

        self.inputbuffer = stdin
        self.byteswritten = 0
        self.outputbuffer = bytes()
        self.errorbuffer = bytes()

        self.stdin = None
        self.stdout = None
        self.stderr = None

        self.outfile = None
        self.errfile = None

        # Other options
        self.verbose = opts.verbose
        try:
            self.print_out = bool(opts.print_out)
        except AttributeError:
            self.print_out = False
        try:
            self.inline = bool(opts.inline)
        except AttributeError:
            self.inline = False
        try:
            self.inline_stdout = bool(opts.inline_stdout)
        except AttributeError:
            self.inline_stdout = False

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
                # 被杀失败，就假定它死了！但是目前还不知道为什么这么假定。
                pass
            self.is_killed = True

    def is_running(self):
        if self.stdin or self.stdout:
            return True
        if self.proc:
            # Popen.poll() 检查子进程是否终止，如果终止返回code，否则返回None
            self.exit_code = self.proc.poll()
            if self.exit_code is None:
                if self.is_killed:
                    self.exit_code = -signal.SIGKILL
                    return False
                else:
                    return True
            else:
                if self.exit_code < 0:
                    msg = f"Killed by signal {-self.exit_code}"
                    self.failures.append(msg)
                elif self.exit_code > 0:
                    msg = f"Exited with error code {self.exit_code}"
                    self.failures.append(msg)
                self.proc = None
                return False

    def log_exception(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        exc = ("Exception: %s, %s, %s" %
               (exc_type, exc_value, traceback.format_tb(exc_traceback)))
        self.failures.append(exc)

    def check_eintr(self, iomap, close_fn):
        _, e, _ = sys.exc_info()
        if e.errno != EINTR:
            close_fn(iomap)
            self.log_exception(e)

    def handle_stdin(self, fd, iomap):
        try:
            start = self.byteswritten
            if start < len(self.inputbuffer):
                chunk = self.inputbuffer[start:start+BUFFER_SIZE]
                self.byteswritten = start + os.write(fd, chunk)
            else:
                self.close_stdin(iomap)
        except (OSError, IOError):
            self.check_eintr(self.close_stdin)


    def handle_stdout(self, fd, iomap):
        try:
            buf = os.read(fd, BUFFER_SIZE)
            if buf:
                if self.inline or self.inline_stdout:
                    self.outputbuffer += buf
                if self.outfile:
                    self.writer.write(self.outfile, buf)
                if self.print_out:
                    sys.stdout.write(f"{self.host}: {buf}")
                    if buf[-1] != '\n':
                        sys.stdout.write('\n')
            else:
                self.close_stdout(iomap)
        except:
            self.check_eintr(self.close_stdout)

    def handle_stderr(self, fd, iomap):
        try:
            buf = os.read(fd, BUFFER_SIZE)
            if buf:
                if self.inline:
                    self.outputbuffer += buf
                if self.errfile:
                    self.writer.write(self.errfile, buf)
            else:
                self.close_stderr(iomap)
        except (OSError, IOError):
            self.check_eintr(self.close_stderr)

    def close_stdin(self, iomap):
        self.close_iomap_fd(iomap, self.stdin)
        self.stdin = None

    def close_stdout(self, iomap):
        self.close_iomap_fd(iomap, self.stdout)
        self.stdout = None
        self.close_write_file(self.outfile)
        self.outfile = None

    def close_stderr(self, iomap):
        self.close_iomap_fd(iomap, self.stderr)
        self.stderr = None
        self.close_write_file(self.errfile)
        self.errfile = None

    def close_iomap_fd(self, iomap, fd):
        if fd:
            iomap.unregister(fd.fileno())
            fd.close()

    def close_write_file(self, file):
        if file:
            self.writer.close(file)

    def timedout(self):
        if not self.killed:
            self._kill()
            self.failures.append("Timed out")

    def cancel(self):
        """未启动时取消Task"""
        self.failures.append("Canceled")

    def elapsed(self):
        """进程耗时"""
        return time.time() - self.timestamp

    def interrupted(self):
        if not self.killed:
            self._kill()
            self.failures.append("Interrupted")

    def report(self, n):
        """任务完成后，打印结果"""
        error_msg = ", ".join(self.failures)
        timestamp = time.asctime().split()[3] # 当前时间 HH:mm:ss
        if color.has_colors(sys.stdout):
            progress = color.c(f"[{color.B(n)}]")
            success = color.g(f"[{color.B('SUCCESS')}]")
            failure = color.r(f"[{color.B('FAILURE')}]")
            stderr = color.r("Stderr: ")
            error_msg = color.r(color.B(error_msg))
        else:
            progress = f"[{n}]"
            success = "[SUCCESS]"
            failure = "[FAILURE]"
            stderr = "Stderr: "
        host = self.pretty_host
        if self.failures:
            p = " ".join((progress, timestamp, failure, host, error_msg))
        else:
            p = " ".join((progress, timestamp, success, host))
        print(p)


if __name__ == '__main__':
    cmd = ['ls', '-l']
    task = Task(cmd)
    task.run()
