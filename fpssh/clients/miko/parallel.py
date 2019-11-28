import gevent
from gevent import Greenlet
from gevent import pool


class FooG(Greenlet):
    def __init__(self):
        super().__init__()

    def switch_out(self):
        print("out")

    def _run(self):
        print('1')
        gevent.sleep(0)
        print('2')


class ParallelSSHClient:

    def __init__(self):
        self.size = 4
        self.pool = pool.Pool(self.size)


g = FooG()
g.start()
g.join()