# Copyright (c) 2009-2010 Denis Bilenko and Eventlet contributors. See LICENSE for details.
from eventlet.support import greenlets as greenlet
from eventlet.hubs import get_hub

__all__ = ['Timeout',
           'with_timeout']

_NONE = object()

try:
    BaseException
except NameError: # Python < 2.5
    class BaseException:
        # not subclassing from object() intentionally, because in
        # that case "raise Timeout" fails with TypeError.
        pass

# deriving from BaseException so that "except Exception, e" doesn't catch
# Timeout exceptions.
class Timeout(BaseException):
    """Raises *exception* in the current greenthread after *timeout* seconds.

    When *exception* is omitted or ``None``, the :class:`Timeout` instance 
    itself is raised. If *seconds* is None, the timer is not scheduled, and is
    only useful if you're planning to raise it directly.
    
    Timeout objects are context managers, and so can be used in with statements.
    When used in a with statement, if *exception* is ``False``, the timeout is
    still raised, but the context manager suppresses it, so the code outside the 
    with-block won't see it.
    """

    def __init__(self, seconds=None, exception=None):
        self.seconds = seconds
        self.exception = exception
        self.timer = None
        self.start()

    def start(self):
        """Schedule the timeout.  This is called on construction, so
        it should not be called explicitly, unless the timer has been 
        cancelled."""
        assert not self.pending, '%r is already started; to restart it, cancel it first' % self
        if self.seconds is None: # "fake" timeout (never expires)
            self.timer = None
        elif self.exception is None or self.exception is False: # timeout that raises self
            self.timer = get_hub().schedule_call_global(self.seconds, greenlet.getcurrent().throw, self)
        else: # regular timeout with user-provided exception
            self.timer = get_hub().schedule_call_global(self.seconds, greenlet.getcurrent().throw, self.exception)
        return self

    @property
    def pending(self):
        """True if the timeout is scheduled to be raised."""
        if self.timer is not None:
            return self.timer.pending
        else:
            return False

    def cancel(self):
        """If the timeout is pending, cancel it.  If not using Timeouts in 
        ``with`` statements, always call cancel() in a ``finally`` after the 
        block of code that is getting timed out.  If not cancelled, the timeout 
        will be raised later on, in some unexpected section of the 
        application."""
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def __repr__(self):
        try:
            classname = self.__class__.__name__
        except AttributeError: # Python < 2.5
            classname = 'Timeout'
        if self.pending:
            pending = ' pending'
        else:
            pending = ''
        if self.exception is None:
            exception = ''
        else:
            exception = ' exception=%r' % self.exception
        return '<%s at %s seconds=%s%s%s>' % (classname, hex(id(self)), self.seconds, exception, pending)

    def __str__(self):
        """
        >>> raise Timeout
        Traceback (most recent call last):
            ...
        Timeout
        """
        if self.seconds is None:
            return ''
        if self.seconds == 1:
            suffix = ''
        else:
            suffix = 's'
        if self.exception is None:
            return '%s second%s' % (self.seconds, suffix)
        elif self.exception is False:
            return '%s second%s (silent)' % (self.seconds, suffix)
        else:
            return '%s second%s (%s)' % (self.seconds, suffix, self.exception)

    def __enter__(self):
        if self.timer is None:
            self.start()
        return self

    def __exit__(self, typ, value, tb):
        self.cancel()
        if value is self and self.exception is False:
            return True


def with_timeout(seconds, function, *args, **kwds):
    """Wrap a call to some (yielding) function with a timeout; if the called
    function fails to return before the timeout, cancel it and return a flag
    value.
    """
    timeout_value = kwds.pop("timeout_value", _NONE)
    timeout = Timeout(seconds)
    try:
        try:
            return function(*args, **kwds)
        except Timeout, ex:
            if ex is timeout and timeout_value is not _NONE:
                return timeout_value
            raise
    finally:
        timeout.cancel()

