# Copyright (c) 2007, Linden Research, Inc.
# Copyright (c) 2007, IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
from sys import stdout
import time
import re
from tests import skipped, skip_with_pyevent, LimitedTestCase, main

from eventlet import tpool, debug
import eventlet

one = 1
two = 2
three = 3
none = None

def noop():
    pass

class TestTpool(LimitedTestCase):
    def setUp(self):
        super(TestTpool, self).setUp()

    def tearDown(self):
        tpool.killall()
        super(TestTpool, self).tearDown()

    @skip_with_pyevent
    def test_wrap_tuple(self):
        my_tuple = (1, 2)
        prox = tpool.Proxy(my_tuple)
        self.assertEqual(prox[0], 1)
        self.assertEqual(prox[1], 2)
        self.assertEqual(len(my_tuple), 2)

    @skip_with_pyevent
    def test_wrap_string(self):
        my_object = "whatever"
        prox = tpool.Proxy(my_object)
        self.assertEqual(str(my_object), str(prox))
        self.assertEqual(len(my_object), len(prox))
        self.assertEqual(my_object.join(['a', 'b']), prox.join(['a', 'b']))

    @skip_with_pyevent
    def test_wrap_uniterable(self):
        # here we're treating the exception as just a normal class
        prox = tpool.Proxy(FloatingPointError())
        def index():
            prox[0]
        def key():
            prox['a']

        self.assertRaises(IndexError, index)
        self.assertRaises(TypeError, key)

    @skip_with_pyevent
    def test_wrap_dict(self):
        my_object = {'a':1}
        prox = tpool.Proxy(my_object)
        self.assertEqual('a', prox.keys()[0])
        self.assertEqual(1, prox['a'])
        self.assertEqual(str(my_object), str(prox))
        self.assertEqual(repr(my_object), repr(prox))
        self.assertEqual(`my_object`, `prox`)

    @skip_with_pyevent
    def test_wrap_module_class(self):
        prox = tpool.Proxy(re)
        self.assertEqual(tpool.Proxy, type(prox))
        exp = prox.compile('.')
        self.assertEqual(exp.flags, 0)
        self.assert_(repr(prox.compile))

    @skip_with_pyevent
    def test_wrap_eq(self):
        prox = tpool.Proxy(re)
        exp1 = prox.compile('.')
        exp2 = prox.compile(exp1.pattern)
        self.assertEqual(exp1, exp2)
        exp3 = prox.compile('/')
        self.assert_(exp1 != exp3)

    @skip_with_pyevent
    def test_wrap_nonzero(self):
        prox = tpool.Proxy(re)
        exp1 = prox.compile('.')
        self.assert_(bool(exp1))
        prox2 = tpool.Proxy([1, 2, 3])
        self.assert_(bool(prox2))

    @skip_with_pyevent
    def test_multiple_wraps(self):
        prox1 = tpool.Proxy(re)
        prox2 = tpool.Proxy(re)
        x1 = prox1.compile('.')
        x2 = prox1.compile('.')
        del x2
        x3 = prox2.compile('.')

    @skip_with_pyevent
    def test_wrap_getitem(self):
        prox = tpool.Proxy([0,1,2])
        self.assertEqual(prox[0], 0)

    @skip_with_pyevent
    def test_wrap_setitem(self):
        prox = tpool.Proxy([0,1,2])
        prox[1] = 2
        self.assertEqual(prox[1], 2)

    @skip_with_pyevent
    def test_raising_exceptions(self):
        prox = tpool.Proxy(re)
        def nofunc():
            prox.never_name_a_function_like_this()
        self.assertRaises(AttributeError, nofunc)

    def assertLessThan(self, a, b):
        self.assert_(a < b, "%s is not less than %s" % (a, b))

    @skip_with_pyevent
    def test_variable_and_keyword_arguments_with_function_calls(self):
        import optparse
        parser = tpool.Proxy(optparse.OptionParser())
        z = parser.add_option('-n', action='store', type='string', dest='n')
        opts,args = parser.parse_args(["-nfoo"])
        self.assertEqual(opts.n, 'foo')

    @skip_with_pyevent
    def test_contention(self):
        from tests import tpool_test
        prox = tpool.Proxy(tpool_test)

        pile = eventlet.GreenPile(4)
        pile.spawn(lambda: self.assertEquals(prox.one, 1))
        pile.spawn(lambda: self.assertEquals(prox.two, 2))
        pile.spawn(lambda: self.assertEquals(prox.three, 3))
        results = list(pile)
        self.assertEquals(len(results), 3)

    @skip_with_pyevent
    def test_timeout(self):
        import time
        eventlet.Timeout(0.1, eventlet.TimeoutError())
        self.assertRaises(eventlet.TimeoutError,
                          tpool.execute, time.sleep, 0.3)

    @skip_with_pyevent
    def test_killall(self):
        tpool.killall()
        tpool.setup()

    @skip_with_pyevent
    def test_autowrap(self):
        x = tpool.Proxy({'a':1, 'b':2}, autowrap=(int,))
        self.assert_(isinstance(x.get('a'), tpool.Proxy))
        self.assert_(not isinstance(x.items(), tpool.Proxy))
        # attributes as well as callables
        from tests import tpool_test
        x = tpool.Proxy(tpool_test, autowrap=(int,))
        self.assert_(isinstance(x.one, tpool.Proxy))
        self.assert_(not isinstance(x.none, tpool.Proxy))

    @skip_with_pyevent
    def test_autowrap_names(self):
        x = tpool.Proxy({'a':1, 'b':2}, autowrap_names=('get',))
        self.assert_(isinstance(x.get('a'), tpool.Proxy))
        self.assert_(not isinstance(x.items(), tpool.Proxy))
        from tests import tpool_test
        x = tpool.Proxy(tpool_test, autowrap_names=('one',))
        self.assert_(isinstance(x.one, tpool.Proxy))
        self.assert_(not isinstance(x.two, tpool.Proxy))

    @skip_with_pyevent
    def test_autowrap_both(self):
        from tests import tpool_test
        x = tpool.Proxy(tpool_test, autowrap=(int,), autowrap_names=('one',))
        self.assert_(isinstance(x.one, tpool.Proxy))
        # violating the abstraction to check that we didn't double-wrap
        self.assert_(not isinstance(x._obj, tpool.Proxy))

class TpoolLongTests(LimitedTestCase):
    TEST_TIMEOUT=60
    @skip_with_pyevent
    def test_a_buncha_stuff(self):
        assert_ = self.assert_
        class Dummy(object):
            def foo(self,when,token=None):
                assert_(token is not None)
                time.sleep(random.random()/200.0)
                return token
        
        def sender_loop(loopnum):
            obj = tpool.Proxy(Dummy())
            count = 100
            for n in xrange(count):
                eventlet.sleep(random.random()/200.0)
                now = time.time()
                token = loopnum * count + n
                rv = obj.foo(now,token=token)
                self.assertEquals(token, rv)
                eventlet.sleep(random.random()/200.0)

        pile = eventlet.GreenPile(10)
        for i in xrange(10):
            pile.spawn(sender_loop,i)
        results = list(pile)
        self.assertEquals(len(results), 10)
        tpool.killall()
        
    @skipped
    def test_benchmark(self):
        """ Benchmark computing the amount of overhead tpool adds to function calls."""
        iterations = 10000
        import timeit
        imports = """
from tests.tpool_test import noop
from eventlet.tpool import execute
        """
        t = timeit.Timer("noop()", imports)
        results = t.repeat(repeat=3, number=iterations)
        best_normal = min(results)

        t = timeit.Timer("execute(noop)", imports)
        results = t.repeat(repeat=3, number=iterations)
        best_tpool = min(results)

        tpool_overhead = (best_tpool-best_normal)/iterations
        print "%s iterations\nTpool overhead is %s seconds per call.  Normal: %s; Tpool: %s" % (
            iterations, tpool_overhead, best_normal, best_tpool)
        tpool.killall()

if __name__ == '__main__':
    main()
