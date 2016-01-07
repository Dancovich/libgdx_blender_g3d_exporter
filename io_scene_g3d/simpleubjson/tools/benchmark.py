# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2014 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution.
#

# <pep8 compliant>

import os
import getopt
import pickle
import sys
import time
import simpleubjson
try:
    import json
except ImportError:
    json = None
try:
    import simplejson
except ImportError:
    simplejson = None
try:
    import ujson
except ImportError:
    ujson = None
try:
    import erlport
except ImportError:
    erlport = None


def timeit(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        return time.time() - start
    return wrapper


def load_case(name):
    fname = os.path.join(os.path.dirname(__file__), '../tests/data', name)
    data = open(fname).read()
    return json.loads(data)


def format_results(lib, version, msg, total, count):
    return '    * [%s @ %s] %s in %f (%f / call)' % (lib, version, msg, total,
                                                     (total / float(count)))


def run_test(func, times, *args, **kwargs):
    tfunc = timeit(lambda: func(*args, **kwargs))
    return sum(tfunc() for i in range(times))


def make_benchmark(name, count):
    data = load_case(name)

    src = simpleubjson.encode(data, spec='draft-8')
    total = run_test(simpleubjson.decode, count, src, spec='draft-8')
    print(format_results('simpleubjson',  simpleubjson.__version__,
                         'Decoded Draft-8', total, count))

    total = run_test(simpleubjson.encode, count, data, spec='draft-8')
    print(format_results('simpleubjson',  simpleubjson.__version__,
                         'Encoded Draft-8', total, count))

    print

    src = simpleubjson.encode(data, spec='draft-9')

    # func = lambda *a, **k: list(simpleubjson.decode(*a, **k))
    def func(*a, **k): return list(simpleubjson.decode(*a, **k))
    total = run_test(func, count, src, spec='draft-9')
    print(format_results('simpleubjson',  simpleubjson.__version__,
                         'Decoded Draft-9', total, count))

    total = run_test(simpleubjson.encode, count, data, spec='draft-9')
    print(format_results('simpleubjson',  simpleubjson.__version__,
                         'Encoded Draft-9', total, count))

    if json:

        print

        total = run_test(json.loads, count, json.dumps(data))
        print(format_results('json_stdlib', json.__version__,
                             'Decoded', total, count))

        total = run_test(json.dumps, count, data)
        print(format_results('json_stdlib', json.__version__,
                             'Encoded', total, count))

    if simplejson:

        print

        simplejson._toggle_speedups(True)
        total = run_test(simplejson.loads, count, simplejson.dumps(data))
        print(format_results('simplejson_c', simplejson.__version__,
                             'Decoded', total, count))

        simplejson._toggle_speedups(True)
        total = run_test(simplejson.dumps, count, data)
        print(format_results('simplejson_c', simplejson.__version__,
                             'Encoded', total, count))

        print

        simplejson._toggle_speedups(False)
        total = run_test(simplejson.loads, count, simplejson.dumps(data))
        print(format_results('simplejson_py', simplejson.__version__,
                             'Decoded', total, count))

        simplejson._toggle_speedups(False)
        total = run_test(simplejson.dumps, count, data)
        print(format_results('simplejson_py', simplejson.__version__,
                             'Encoded', total, count))

    if ujson:

        print

        total = run_test(ujson.decode, count, ujson.encode(data))
        print(format_results('ujson', ujson.__version__,
                             'Decoded', total, count))

        total = run_test(ujson.encode, count, data)
        print(format_results('ujson', ujson.__version__,
                             'Encoded', total, count))

    if erlport:

        print

        total = run_test(erlport.decode, count, erlport.encode(data))
        print(format_results('erlport', erlport.__version__,
                             'Decoded', total, count))

        total = run_test(erlport.encode, count, data)
        print(format_results('erlport', erlport.__version__,
                             'Encoded', total, count))

    print

    total = run_test(pickle.loads, count, pickle.dumps(data))
    print(format_results('pickle', pickle.__version__,
                         'Decoded', total, count))

    total = run_test(pickle.dumps, count, data)
    print(format_results('pickle', pickle.__version__,
                         'Encoded', total, count))


def test_1(count):
    print('* [test_1] CouchDB4k.compact.json %d times' % count)
    make_benchmark('CouchDB4k.compact.json', count)
    print
    print


def test_2(count):
    print('* [test_2] MediaContent.compact.json %d times' % count)
    make_benchmark('MediaContent.compact.json', count)
    print
    print


def test_3(count):
    print('* [test_3] TwitterTimeline.compact.json %d times' % count)
    make_benchmark('TwitterTimeline.compact.json', count)
    print
    print


def run(count):
    print('sys.version : %r' % (sys.version,))
    print('sys.platform : %r' % (sys.platform,))
    test_1(count)
    test_2(count)
    test_3(count)


def main():
    """benchmark.py - UBJSON vs JSON performance test script.

    Usage:
        -h, --help      Prints this help
        -c, --count=    Rounds per test.
                        Default: 1000.
    """
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hc:', ['help', 'count='])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)
    count = 100000
    for key, value in opts:
        print(key, value)
        if key in ('-h', '--help'):
            print(main.__doc__)
            sys.exit()
        elif key in ('-c', '--count'):
            count = int(value)
        else:
            assert False, 'unhandled option %s' % key
    run(count)

if __name__ == '__main__':
    main()
