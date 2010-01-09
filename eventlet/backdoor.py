import socket
import sys
import errno
from code import InteractiveConsole

from eventlet import api, hubs
from eventlet.support import greenlets

try:
    sys.ps1
except AttributeError:
    sys.ps1 = '>>> '
try:
    sys.ps2
except AttributeError:
    sys.ps2 = '... '


class FileProxy(object):
    def __init__(self, f):
        self.f = f
        def writeflush(*a, **kw):
            f.write(*a, **kw)
            f.flush()
        self.fixups = {
            'softspace': 0,
            'isatty': lambda: True,
            'flush': lambda: None,
            'write': writeflush,
            'readline': lambda *a: f.readline(*a).replace('\r\n', '\n'),
        }

    def __getattr__(self, attr):
        fixups = object.__getattribute__(self, 'fixups')
        if attr in fixups:
            return fixups[attr]    
        f = object.__getattribute__(self, 'f')
        return getattr(f, attr)


class SocketConsole(greenlets.greenlet):
    def __init__(self, desc, hostport, locals):
        self.hostport = hostport
        self.locals = locals
        # mangle the socket
        self.desc = FileProxy(desc)
        greenlets.greenlet.__init__(self)

    def run(self):
        try:
            console = InteractiveConsole(self.locals)
            console.interact()
        finally:
            self.switch_out()
            self.finalize()

    def switch(self, *args, **kw):
        self.saved = sys.stdin, sys.stderr, sys.stdout
        sys.stdin = sys.stdout = sys.stderr = self.desc
        greenlets.greenlet.switch(self, *args, **kw)

    def switch_out(self):
        sys.stdin, sys.stderr, sys.stdout = self.saved

    def finalize(self):
        # restore the state of the socket
        self.desc = None
        print "backdoor closed to %s:%s" % self.hostport


def backdoor_server(sock, locals=None):
    """ Blocking function that runs a backdoor server on the socket *sock*, 
    accepting connections and running backdoor consoles for each client that
    connects.
    """
    print "backdoor server listening on %s:%s" % sock.getsockname()
    try:
        try:
            while True:
                socketpair = sock.accept()
                backdoor(socketpair, locals)
        except socket.error, e:
            # Broken pipe means it was shutdown
            if e[0] != errno.EPIPE:
                raise
    finally:
        sock.close()


def backdoor((conn, addr), locals=None):
    """Sets up an interactive console on a socket with a single connected
    client.  This does not block the caller, as it spawns a new greenlet to 
    handle the console.  This is meant to be called from within an accept loop
    (such as backdoor_server).
    """
    host, port = addr
    print "backdoor to %s:%s" % (host, port)
    fl = conn.makefile("rw")
    console = SocketConsole(fl, (host, port), locals)
    hub = hubs.get_hub()
    hub.schedule_call_global(0, console.switch)


if __name__ == '__main__':
    backdoor_server(api.tcp_listener(('127.0.0.1', 9000)), {})

