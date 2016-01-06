# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2014 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution.
#

# <pep8 compliant>

import sys

version = '.'.join(map(str, sys.version_info[:2]))

if version >= '3.0':
    from io import BytesIO
    basestring = (str, bytes)
    unicode = str
    bytes = bytes
    long = int
    xrange = range

    d = {}
    dict_keysiterator = type(d.keys())
    dict_valuesiterator = type(d.values())
    dict_itemsiterator = type(d.items())
else:
    from cStringIO import StringIO as BytesIO
    basestring = basestring
    unicode = unicode
    b = bytes = str
    long = long
    xrange = xrange

    d = {}
    dict_keysiterator = type(d.iterkeys())
    dict_valuesiterator = type(d.itervalues())
    dict_itemsiterator = type(d.iteritems())

try:
    from math import isinf, isnan
except ImportError:  # < Python 2.6
    def isinf(v):
        return v == float('inf') or v == float('-inf')

    def isnan(v):
        return isinstance(v, float) and str(v) == 'nan'


# b = lambda s: isinstance(s, unicode) and s.encode('latin1') or s
def b(s): return isinstance(s, unicode) and s.encode('latin1') or s


# u = lambda s: isinstance(s, bytes) and s.decode('utf-8') or s
def u(s): return isinstance(s, bytes) and s.decode('utf-8') or s
XRangeType = type(xrange(0))
