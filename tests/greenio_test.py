import socket as _orig_sock
from tests import LimitedTestCase, skip_with_pyevent, main, skipped
from eventlet import event
from eventlet import greenio
from eventlet import debug
from eventlet.green import socket
from eventlet.green import time
from eventlet.green.socket import GreenSSLObject
import errno

import eventlet
import os
import sys
import array

def bufsized(sock, size=1):
    """ Resize both send and receive buffers on a socket.
    Useful for testing trampoline.  Returns the socket.

    >>> import socket
    >>> sock = bufsized(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, size)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, size)
    return sock

def min_buf_size():
    """Return the minimum buffer size that the platform supports."""
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1)
    return test_sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)

class TestGreenIo(LimitedTestCase):
    def test_connect_timeout(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        gs = greenio.GreenSocket(s)
        try:
            gs.connect(('192.0.2.1', 80))
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')
        except socket.error, e:
            # unreachable is also a valid outcome
            if not e[0] in (errno.EHOSTUNREACH, errno.ENETUNREACH):
                raise

    def test_accept_timeout(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        s.listen(50)

        s.settimeout(0.1)
        gs = greenio.GreenSocket(s)
        try:
            gs.accept()
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

    def test_connect_ex_timeout(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        gs = greenio.GreenSocket(s)
        e = gs.connect_ex(('192.0.2.1', 80))
        if not e in (errno.EHOSTUNREACH, errno.ENETUNREACH):
            self.assertEquals(e, errno.EAGAIN)

    def test_recv_timeout(self):
        listener = greenio.GreenSocket(socket.socket())
        listener.bind(('', 0))
        listener.listen(50)
        
        evt = event.Event()
        def server():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            evt.wait()

        gt = eventlet.spawn(server)

        addr = listener.getsockname()

        client = greenio.GreenSocket(socket.socket())
        client.settimeout(0.1)

        client.connect(addr)

        try:
            r = client.recv(8192)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_recvfrom_timeout(self):
        gs = greenio.GreenSocket(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        gs.settimeout(.1)
        gs.bind(('', 0))

        try:
            gs.recvfrom(8192)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

    def test_recvfrom_into_timeout(self):
        buf = buffer(array.array('B'))

        gs = greenio.GreenSocket(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        gs.settimeout(.1)
        gs.bind(('', 0))

        try:
            gs.recvfrom_into(buf)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

    def test_recv_into_timeout(self):
        buf = buffer(array.array('B'))

        listener = greenio.GreenSocket(socket.socket())
        listener.bind(('', 0))
        listener.listen(50)

        evt = event.Event()
        def server():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            evt.wait()

        gt = eventlet.spawn(server)

        addr = listener.getsockname()

        client = greenio.GreenSocket(socket.socket())
        client.settimeout(0.1)

        client.connect(addr)

        try:
            r = client.recv_into(buf)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_send_timeout(self):
        listener = bufsized(eventlet.listen(('', 0)))

        evt = event.Event()
        def server():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            sock = bufsized(sock)
            evt.wait()

        gt = eventlet.spawn(server)

        addr = listener.getsockname()

        client = bufsized(greenio.GreenSocket(socket.socket()))
        client.connect(addr)
        try:
            client.settimeout(0.00001)
            msg = "A"*(100000)  # large enough number to overwhelm most buffers

            total_sent = 0
            # want to exceed the size of the OS buffer so it'll block in a
            # single send
            for x in range(10):
                total_sent += client.send(msg)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_sendall_timeout(self):
        listener = greenio.GreenSocket(socket.socket())
        listener.bind(('', 0))
        listener.listen(50)

        evt = event.Event()
        def server():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            evt.wait()

        gt = eventlet.spawn(server)

        addr = listener.getsockname()

        client = greenio.GreenSocket(socket.socket())
        client.settimeout(0.1)
        client.connect(addr)

        try:
            msg = "A"*(8*1024*1024)

            # want to exceed the size of the OS buffer so it'll block
            client.sendall(msg)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_close_with_makefile(self):
        def accept_close_early(listener):
            # verify that the makefile and the socket are truly independent
            # by closing the socket prior to using the made file
            try:
                conn, addr = listener.accept()
                fd = conn.makefile()
                conn.close()
                fd.write('hello\n')
                fd.close()
                # socket._fileobjects are odd: writes don't check
                # whether the socket is closed or not, and you get an
                # AttributeError during flush if it is closed
                fd.write('a')
                self.assertRaises(Exception, fd.flush)
                self.assertRaises(socket.error, conn.send, 'b')
            finally:
                listener.close()

        def accept_close_late(listener):
            # verify that the makefile and the socket are truly independent
            # by closing the made file and then sending a character
            try:
                conn, addr = listener.accept()
                fd = conn.makefile()
                fd.write('hello')
                fd.close()
                conn.send('\n')
                conn.close()
                fd.write('a')
                self.assertRaises(Exception, fd.flush)
                self.assertRaises(socket.error, conn.send, 'b')
            finally:
                listener.close()

        def did_it_work(server):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', server.getsockname()[1]))
            fd = client.makefile()
            client.close()
            assert fd.readline() == 'hello\n'
            assert fd.read() == ''
            fd.close()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 0))
        server.listen(50)
        killer = eventlet.spawn(accept_close_early, server)
        did_it_work(server)
        killer.wait()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 0))
        server.listen(50)
        killer = eventlet.spawn(accept_close_late, server)
        did_it_work(server)
        killer.wait()

    def test_del_closes_socket(self):
        def accept_once(listener):
            # delete/overwrite the original conn
            # object, only keeping the file object around
            # closing the file object should close everything
            try:
                conn, addr = listener.accept()
                conn = conn.makefile()
                conn.write('hello\n')
                conn.close()
                conn.write('a')
                self.assertRaises(Exception, conn.flush)
            finally:
                listener.close()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))
        server.listen(50)
        killer = eventlet.spawn(accept_once, server)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', server.getsockname()[1]))
        fd = client.makefile()
        client.close()
        assert fd.read() == 'hello\n'
        assert fd.read() == ''

        killer.wait()

    def test_full_duplex(self):
        large_data = '*' * 10 * min_buf_size()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        listener.listen(50)
        bufsized(listener)

        def send_large(sock):
            sock.sendall(large_data)

        def read_large(sock):
            result = sock.recv(len(large_data))
            expected = 'hello world'
            while len(result) < len(large_data):
                result += sock.recv(len(large_data))
            self.assertEquals(result, large_data)

        def server():
            (sock, addr) = listener.accept()
            sock = bufsized(sock)
            send_large_coro = eventlet.spawn(send_large, sock)
            eventlet.sleep(0)
            result = sock.recv(10)
            expected = 'hello world'
            while len(result) < len(expected):
                result += sock.recv(10)
            self.assertEquals(result, expected)
            send_large_coro.wait()

        server_evt = eventlet.spawn(server)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', listener.getsockname()[1]))
        bufsized(client)
        large_evt = eventlet.spawn(read_large, client)
        eventlet.sleep(0)
        client.sendall('hello world')
        server_evt.wait()
        large_evt.wait()
        client.close()

    def test_sendall(self):
        # test adapted from Marcus Cavanaugh's email
        # it may legitimately take a while, but will eventually complete
        self.timer.cancel()
        second_bytes = 10
        def test_sendall_impl(many_bytes):
            bufsize = max(many_bytes/15, 2)
            def sender(listener):
                (sock, addr) = listener.accept()
                sock = bufsized(sock, size=bufsize)
                sock.sendall('x'*many_bytes)
                sock.sendall('y'*second_bytes)

            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
            listener.bind(("", 0))
            listener.listen(50)
            sender_coro = eventlet.spawn(sender, listener)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', listener.getsockname()[1]))
            bufsized(client, size=bufsize)
            total = 0
            while total < many_bytes:
                data = client.recv(min(many_bytes - total, many_bytes/10))
                if data == '':
                    break
                total += len(data)

            total2 = 0
            while total < second_bytes:
                data = client.recv(second_bytes)
                if data == '':
                    break
                total2 += len(data)

            sender_coro.wait()
            client.close()

        for bytes in (1000, 10000, 100000, 1000000):
            test_sendall_impl(bytes)

    def test_wrap_socket(self):
        try:
            import ssl
        except ImportError:
            pass  # pre-2.6
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', 0))
            sock.listen(50)
            ssl_sock = ssl.wrap_socket(sock)

    def test_timeout_and_final_write(self):
        # This test verifies that a write on a socket that we've
        # stopped listening for doesn't result in an incorrect switch
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))
        server.listen(50)
        bound_port = server.getsockname()[1]

        def sender(evt):
            s2, addr = server.accept()
            wrap_wfile = s2.makefile()

            eventlet.sleep(0.02)
            wrap_wfile.write('hi')
            s2.close()
            evt.send('sent via event')

        from eventlet import event
        evt = event.Event()
        eventlet.spawn(sender, evt)
        eventlet.sleep(0)  # lets the socket enter accept mode, which
                      # is necessary for connect to succeed on windows
        try:
            # try and get some data off of this pipe
            # but bail before any is sent
            eventlet.Timeout(0.01)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', bound_port))
            wrap_rfile = client.makefile()
            _c = wrap_rfile.read(1)
            self.fail()
        except eventlet.TimeoutError:
            pass

        result = evt.wait()
        self.assertEquals(result, 'sent via event')
        server.close()
        client.close()

    def test_pipe_read(self):
        # ensure that 'readline' works properly on GreenPipes when data is not
        # immediately available (fd is nonblocking, was raising EAGAIN)
        # also ensures that readline() terminates on '\n' and '\r\n'
        r, w = os.pipe()

        r = os.fdopen(r)
        w = os.fdopen(w, 'w')

        r = greenio.GreenPipe(r)
        w = greenio.GreenPipe(w)

        def writer():
            eventlet.sleep(.1)

            w.write('line\n')
            w.flush()

            w.write('line\r\n')
            w.flush()

        gt = eventlet.spawn(writer)

        eventlet.sleep(0)

        line = r.readline()
        self.assertEquals(line, 'line\n')

        line = r.readline()
        self.assertEquals(line, 'line\r\n')

        gt.wait()


class TestGreenIoLong(LimitedTestCase):
    TEST_TIMEOUT=10  # the test here might take a while depending on the OS
    @skip_with_pyevent
    def test_multiple_readers(self, clibufsize=False):
        recvsize = 2 * min_buf_size()
        sendsize = 10 * recvsize
        # test that we can have multiple coroutines reading
        # from the same fd.  We make no guarantees about which one gets which
        # bytes, but they should both get at least some
        def reader(sock, results):
            while True:
                data = sock.recv(recvsize)
                if data == '':
                    break
                results.append(data)

        results1 = []
        results2 = []
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        listener.listen(50)
        def server():
            (sock, addr) = listener.accept()
            sock = bufsized(sock)
            try:
                c1 = eventlet.spawn(reader, sock, results1)
                c2 = eventlet.spawn(reader, sock, results2)
                try:
                    c1.wait()
                    c2.wait()
                finally:
                    c1.kill()
                    c2.kill()
            finally:
                sock.close()

        server_coro = eventlet.spawn(server)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', listener.getsockname()[1]))
        if clibufsize:
            bufsized(client, size=sendsize)
        else:
            bufsized(client)
        client.sendall('*' * sendsize)
        client.close()
        server_coro.wait()
        listener.close()
        self.assert_(len(results1) > 0)
        self.assert_(len(results2) > 0)

    @skipped  # by rdw because it fails but it's not clear how to make it pass
    @skip_with_pyevent
    def test_multiple_readers2(self):
        self.test_multiple_readers(clibufsize=True)

class TestGreenIoStarvation(LimitedTestCase):    
    # fixme: this doesn't succeed, because of eventlet's predetermined
    # ordering.  two processes, one with server, one with client eventlets
    # might be more reliable?
    
    TEST_TIMEOUT=300  # the test here might take a while depending on the OS
    @skipped  # by rdw, because it fails but it's not clear how to make it pass
    @skip_with_pyevent
    def test_server_starvation(self, sendloops=15):
        recvsize = 2 * min_buf_size()
        sendsize = 10000 * recvsize
        
        results = [[] for i in xrange(5)]
        
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        listener.listen(50)
        
        base_time = time.time()
        
        def server(my_results):
            (sock, addr) = listener.accept()
            
            datasize = 0
            
            t1 = None
            t2 = None
            try:
                while True:
                    data = sock.recv(recvsize)
                    if not t1:
                        t1 = time.time() - base_time
                    if data == '':
                        t2 = time.time() - base_time
                        my_results.append(datasize)
                        my_results.append((t1,t2))
                        break
                    datasize += len(data)
            finally:
                sock.close()

        def client():
            pid = os.fork()
            if pid:
                return pid
    
            client = _orig_sock.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', port))

            bufsized(client, size=sendsize)

            for i in range(sendloops):
                client.sendall('*' * sendsize)
            client.close()
            os._exit(0)

        clients = []
        servers = []
        for r in results:
            servers.append(eventlet.spawn(server, r))
        for r in results:
            clients.append(client())

        for s in servers:
            s.wait()
        for c in clients:
            os.waitpid(c, 0)

        listener.close()

        # now test that all of the server receive intervals overlap, and
        # that there were no errors.
        for r in results:
            assert len(r) == 2, "length is %d not 2!: %s\n%s" % (len(r), r, results)
            assert r[0] == sendsize * sendloops
            assert len(r[1]) == 2
            assert r[1][0] is not None
            assert r[1][1] is not None

        starttimes = sorted(r[1][0] for r in results)
        endtimes = sorted(r[1][1] for r in results)
        runlengths = sorted(r[1][1] - r[1][0] for r in results)

        # assert that the last task started before the first task ended
        # (our no-starvation condition)
        assert starttimes[-1] < endtimes[0], "Not overlapping: starts %s ends %s" % (starttimes, endtimes)

        maxstartdiff = starttimes[-1] - starttimes[0]

        assert maxstartdiff * 2 < runlengths[0], "Largest difference in starting times more than twice the shortest running time!"
        assert runlengths[0] * 2 > runlengths[-1], "Longest runtime more than twice as long as shortest!"

if __name__ == '__main__':
    main()
