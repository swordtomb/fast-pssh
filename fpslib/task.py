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

        self.host = host
        self.pretty_host = host
        self.port = port
        self.cmd = cmd

        if user != opts.user:
            self.pretty_host = '@'.join((user, self.pretty_host))
        if port:
            self.pretty_host = ':'.join((self.pretty_host, port))

        self.proc = None
        self.writer = None
        self.timestamp = None
        self.failures = []
        self.killed = False

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

    def start(self, node_num, node_count, iomap, writer):
        # 线程写
        self.writer = writer
        if writer:
            self.outfile, self.errfile = writer.open_files(self.pertty_host)

        # 设置环境变量
        env = os.environ.copy()
        env["PSSH_NODE_NUM"] = str(node_num)
        env["PSSH_NODE_COUNT"] = str(node_count)
        env["PSSH_HOST"] = self.host
        # close_fds=True作用是子进程除了0,1,2其他描述符都关闭了
        # setsid 子进程自己属于一个进程组
        # 所有设置成PIPE与主进程建立管道
        self.proc = Popen(self.cmd, stdin=PIPE, stderr=PIPE, stdout=PIPE,
                          close_fds=True, preexec_fn=os.setsid, env=env)
        self.timestamp = time.time()

        # TODO SSH_ASKPASS
        if "DISPLAY" not in env:
            env["DISPLAY"] = "pssh-gibberish"

        if self.inputbuffer:
            self.stdin = self.proc.stdin
            iomap.register_write(self.stdin.fileno(), self.handle_stdin)
        else:
            self.proc.stdin.close()
        self.stdout = self.proc.stdout
        iomap.register_read(self.stdout.fileno(), self.handle_stdout)
        self.stderr = self.proc.stderr
        iomap.register_read(self.stderr.fileno(), self.handle_stderr)

    def _kill(self):
        if self.proc:
            try:
                # -pid 杀死 杀进程组
                os.kill(-self.proc.pid, signal.SIGKILL)
            except OSError:
                # 杀失败，就假定它死了！
                pass
            self.killed = True

    def timedout(self):
        if not self.killed:
            self._kill()
            self.failures.append("Timed out")

    def interrupted(self):
        if not self.killed:
            self._kill()
            self.failures.append("Interrupted")

    def cancel(self):
        """未启动时取消Task"""
        self.failures.append("Canceled")

    def elapsed(self):
        """进程耗时"""
        return time.time() - self.timestamp

    def is_running(self):
        # 输入输出还没处理完，处理完会将fd置None。
        if self.stdin or self.stdout:
            return True
        if self.proc:
            # Popen.poll() 检查子进程是否终止，如果终止返回code，否则返回None
            self.exit_code = self.proc.poll()
            if self.exit_code is None:
                if self.killed:
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

    def handle_stdin(self, fd, iomap):
        try:
            start = self.byteswritten
            if start < len(self.inputbuffer):
                chunk = self.inputbuffer[start:start+BUFFER_SIZE]
                self.byteswritten = start + os.write(fd, chunk)
            else:
                self.close_stdin(iomap)
        except (OSError, IOError):
            self.check_eintr(iomap, self.close_stdin)

    def close_stdin(self, iomap):
        self.close_iomap_fd(iomap, self.stdin)
        self.stdin = None

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
        except (OSError, IOError):
            self.check_eintr(iomap, self.close_stdout)

    def close_stdout(self, iomap):
        self.close_iomap_fd(iomap, self.stdout)
        self.stdout = None
        self.close_write_file(self.outfile)
        self.outfile = None

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
            self.check_eintr(iomap, self.close_stderr)

    def close_stderr(self, iomap):
        self.close_iomap_fd(iomap, self.stderr)
        self.stderr = None
        self.close_write_file(self.errfile)
        self.errfile = None

    def log_exception(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        exc = ("Exception: %s, %s, %s" %
               (exc_type, exc_value, exc_traceback.format_tb(exc_traceback)))
        self.failures.append(exc)

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
            p = ' '.join((progress, timestamp, failure, host, error_msg))
        else:
            p = ' '.join((progress, timestamp, success, host))
        print(p)

        # 刷新保证输出顺序。stdout遇到换行符会打印缓冲区中内容，没有手动flush()会打印。
        if self.outputbuffer:
            sys.stdout.flush()
            try:
                sys.stdout.buffer.write(self.outputbuffer)
                sys.stdout.flush()
            except AttributeError:
                sys.stdout.write(self.outputbuffer)
        if self.errorbuffer:
            sys.stdout.flush()
            try:
                sys.stdout.buffer.write(self.errorbuffer)
            except AttributeError:
                sys.stdout.write(self.errorbuffer)

    @staticmethod
    def close_iomap_fd(iomap, fd):
        if fd:
            iomap.unregister(fd.fileno())
            fd.close()

    def close_write_file(self, file):
        if file:
            self.writer.close(file)

    def check_eintr(self, iomap, close_fn):
        _, e, _ = sys.exc_info()
        if e.errno != EINTR:
            close_fn(iomap)
            self.log_exception(e)


if __name__ == '__main__':
    cmd = ['ls', '-l']
    task = Task(cmd)
    task.run()
