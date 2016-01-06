# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2014 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution.
#

from decimal import Decimal
from struct import pack, unpack
from . import NOOP as NOOP_SENTINEL
from .compat import (
    BytesIO, basestring, b, bytes, unicode, long, xrange,
    dict_itemsiterator, dict_keysiterator, dict_valuesiterator,
    isinf, isnan
)
from .exceptions import (
    EncodeError, MarkerError, EarlyEndOfStreamError
)


NOOP = b('N')
NULL = b('Z')
FALSE = b('F')
TRUE = b('T')
INT8 = b('i')
UINT8 = b('U')
INT16 = b('I')
INT32 = b('l')
INT64 = b('L')
FLOAT = b('d')
DOUBLE = b('D')
CHAR = b('C')
STRING = b('S')
HIDEF = b('H')
ARRAY_OPEN = b('[')
ARRAY_CLOSE = b(']')
OBJECT_OPEN = b('{')
OBJECT_CLOSE = b('}')

BOS_A = object()
BOS_O = object()

CONSTANTS = set([NOOP, NULL, FALSE, TRUE])
CONTAINERS = set([ARRAY_OPEN, ARRAY_CLOSE, OBJECT_OPEN, OBJECT_CLOSE])
NUMBERS = set([INT8, UINT8, INT16, INT32, INT64, FLOAT, DOUBLE])
STRINGS = set([STRING, HIDEF])
OBJECT_KEYS = set([CHAR, STRING])

CHARS = dict((i, b(chr(i))) for i in range(256))

__all__ = ['Draft9Decoder', 'Draft9Encoder']


class Draft9Decoder(object):
    """Decoder of UBJSON data to Python object following Draft 9 specification
    and using next data mapping:

    +--------+----------------------------+----------------------------+-------+
    | Marker | UBJSON type                | Python type                | Notes |
    +========+============================+============================+=======+
    | ``N``  | noop                       | :const:`~simpleubjson.NOOP`| \(1)  |
    +--------+----------------------------+----------------------------+-------+
    | ``Z``  | null                       | None                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``F``  | false                      | bool                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``T``  | true                       | bool                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``i``  | int8                       | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``U``  | uint8                      | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``I``  | int16                      | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``l``  | int32                      | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``L``  | int64                      | long                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``d``  | float                      | float                      |       |
    +--------+----------------------------+----------------------------+-------+
    | ``D``  | double                     | float                      |       |
    +--------+----------------------------+----------------------------+-------+
    | ``H``  | hidef                      | decimal.Decimal            |       |
    +--------+----------------------------+----------------------------+-------+
    | ``C``  | char                       | unicode                    |       |
    +--------+----------------------------+----------------------------+-------+
    | ``S``  | string                     | unicode                    |       |
    +--------+----------------------------+----------------------------+-------+
    | ``[``  | array                      | generator                  | \(2)  |
    +--------+----------------------------+----------------------------+-------+
    | ``{``  | object                     | generator                  | \(3)  |
    +--------+----------------------------+----------------------------+-------+

    Notes:

    (1)
        `NoOp` values are ignored by default if only `allow_noop` argument
        wasn't passed as ``True``.

    (2)
        Nested generators are automatically converted into lists.

    (3)
        Unsized objects are represented as list of 2-element tuple with object
        key and value.
    """
    dispatch = {}

    def __init__(self, source, allow_noop=False):
        if isinstance(source, unicode):
            source = source.encode('utf-8')
        if isinstance(source, bytes):
            source = BytesIO(source)
        self.read = source.read
        self.allow_noop = allow_noop
        self.dispatch = self.dispatch.copy()

    def __iter__(self):
        return self

    def next_tlv(self):
        tag = self.read(1)
        while tag == NOOP and not self.allow_noop:
            tag = self.read(1)
        if tag in NUMBERS:
            if tag == INT8:
                # Trivial operations for trivial cases saves a lot of time
                value = ord(self.read(1))
                if value > 128:
                    value -= 256
                    #value, = unpack('>b', self.read(1))
            elif tag == UINT8:
                value = ord(self.read(1))
            elif tag == INT16:
                value, = unpack('>h', self.read(2))
            elif tag == INT32:
                value, = unpack('>i', self.read(4))
            elif tag == INT64:
                value, = unpack('>q', self.read(8))
            elif tag == FLOAT:
                value, = unpack('>f', self.read(4))
            elif tag == DOUBLE:
                value, = unpack('>d', self.read(8))
            else:
                raise MarkerError('tag %r not in NUMBERS %r' % (tag, NUMBERS))
            return tag, None, value
        elif tag in STRINGS:
            # Don't be recursive for string length calculation to save time
            ltag = self.read(1)
            if ltag == INT8:
                length = ord(self.read(1))
                if length > 128:
                    length -= 256
            elif ltag == UINT8:
                length = ord(self.read(1))
            elif ltag == INT16:
                length, = unpack('>h', self.read(2))
            elif ltag == INT32:
                length, = unpack('>i', self.read(4))
            elif ltag == INT64:
                length, = unpack('>q', self.read(8))
            elif not ltag:
                raise EarlyEndOfStreamError('string length marker missed')
            else:
                raise MarkerError('invalid string size marker 0x%02X (%r)'
                                  '' % (ord(ltag), ltag))
            return tag, length, self.read(length)
        elif tag == CHAR:
            return tag, None, self.read(1)
        elif tag in CONSTANTS or tag in CONTAINERS:
            return tag, None, None
        elif not tag:
            raise EarlyEndOfStreamError('nothing to decode')
        else:
            raise MarkerError('invalid marker 0x%02x (%r)' % (ord(tag), tag))

    def decode_next(self):
        tag, length, value = self.next_tlv()
        return self.dispatch[tag](self, tag, length, value)

    __next__ = next = decode_next

    def decode_noop(self, tag, length, value):
        return NOOP_SENTINEL
    dispatch[NOOP] = decode_noop

    def decode_none(self, tag, length, value):
        return None
    dispatch[NULL] = decode_none

    def decode_false(self, tag, length, value):
        return False
    dispatch[FALSE] = decode_false

    def decode_true(self, tag, length, value):
        return True
    dispatch[TRUE] = decode_true

    def decode_int(self, tag, length, value):
        return value
    dispatch[INT8] = decode_int
    dispatch[UINT8] = decode_int
    dispatch[INT16] = decode_int
    dispatch[INT32] = decode_int
    dispatch[INT64] = decode_int

    def decode_float(self, tag, length, value):
        return value
    dispatch[FLOAT] = decode_float
    dispatch[DOUBLE] = decode_float

    def decode_char(self, tag, length, value):
        return value.decode('latin-1')
    dispatch[CHAR] = decode_char

    def decode_string(self, tag, length, value):
        return value.decode('utf-8')
    dispatch[STRING] = decode_string

    def decode_hidef(self, tag, length, value):
        return Decimal(value.decode('utf-8'))
    dispatch[HIDEF] = decode_hidef

    def decode_array_stream(self, tag, length, value):
        dispatch = self.dispatch
        next_tlv = self.next_tlv
        array_close = ARRAY_CLOSE
        container_openers = set([ARRAY_OPEN, OBJECT_OPEN])
        def array_stream():
            while 1:
                tag, length, value = next_tlv()
                if tag == array_close:
                    break
                item = dispatch[tag](self, tag, length, value)
                if tag in container_openers:
                    yield list(item)
                else:
                    yield item
        return array_stream()
    dispatch[ARRAY_OPEN] = decode_array_stream

    def decode_array_close(self, tag, length, value):
        raise EarlyEndOfStreamError
    dispatch[ARRAY_CLOSE] = decode_array_close

    def decode_object_stream(self, tag, length, value):
        def object_stream():
            key = None
            dispatch = self.dispatch
            next_tlv = self.next_tlv
            noop = NOOP
            noop_sentinel = NOOP_SENTINEL
            object_close = OBJECT_CLOSE
            container_openers = set([ARRAY_OPEN, OBJECT_OPEN])
            object_keys = OBJECT_KEYS
            while 1:
                tag, length, value = next_tlv()
                if tag == noop and key is None:
                    yield noop_sentinel, noop_sentinel
                elif tag == noop and key:
                    continue
                elif tag == object_close:
                    if key:
                        raise EarlyEndOfStreamError(
                            'value missed for key %r' % key)
                    break
                elif key is None and tag not in object_keys:
                    raise MarkerError('key should be string, got %r' % (tag))
                else:
                    value = dispatch[tag](self, tag, length, value)
                    if key is None:
                        key = value
                    elif tag in container_openers:
                        yield key, list(value)
                        key = None
                    else:
                        yield key, value
                        key = None
        return object_stream()
    dispatch[OBJECT_OPEN] = decode_object_stream

    def decode_object_close(self, tag, length, value):
        raise EarlyEndOfStreamError
    dispatch[OBJECT_CLOSE] = decode_object_close


class Draft9Encoder(object):
    """Encoder of Python objects into UBJSON data following Draft 9
    specification rules with next data mapping:

    +-----------------------------+------------------------------------+-------+
    | Python type                 | UBJSON type                        | Notes |
    +=============================+=======+============================+=======+
    | :const:`~simpleubjson.NOOP` | NoOp                               |       |
    +-----------------------------+------------------------------------+-------+
    | :const:`None`               | null                               |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`bool`               | :const:`False` => false            |       |
    |                             | :const:`True`  => true             |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`int`,               | `integer` or `hidef`               | \(1)  |
    | :class:`long`               |                                    |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`float`              | `float`, `null` or `hidef`         | \(2)  |
    +-----------------------------+------------------------------------+-------+
    | :class:`str`,               | char or string                     | \(3)  |
    | :class:`unicode`            |                                    |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`tuple`,             | array                              |       |
    | :class:`list`,              |                                    |       |
    | :class:`generator`,         |                                    |       |
    | :class:`set`,               |                                    |       |
    | :class:`frozenset`,         |                                    |       |
    | :class:`XRange`             |                                    |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`dict`,              | object                             | \(4)  |
    | :class:`dict_itemsiterator` |                                    |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`decimal.Decimal`    | hidef                              |       |
    +-----------------------------+------------------------------------+-------+

    Notes:

    (1)
        Depending on value it may be encoded into various UBJSON types:

        * [-2^7, 2^7): ``int8``
        * [0, 2^8): ``uint8``
        * [-2^15, 2^15): ``int16``
        * [-2^31, 2^31): ``int32``
        * [-2^63, 2^63): ``int64``
        * everything bigger/smaller: ``huge``

    (2)
        Depending on value it may be encoded into various UBJSON types:

        * 1.18e-38 <= abs(value) <= 3.4e38: ``float``
        * 2.23e-308 <= abs(value) < 1.8e308: ``double``
        * :const:`inf`, :const:`-inf`: ``null``
        * everything bigger/smaller: ``huge``

    (3)
        Unicode string are been encoded with utf-8 charset. Byte strings are
        required to have `utf-8` encoding or :exc:`simpleubjson.EncodeError`
        will be raised.
        If string contains only single character that has code in range 0-255,
        it will be encoded as ``char`` type.

    (4)
        Dict keys should have string type or :exc:`simpleubjson.EncodeError`
        will be raised.
    """

    dispatch = {}

    def __init__(self, default=None):
        self._default = default or self.default

    def default(self, obj):
        raise EncodeError('unable to encode %r' % obj)

    def encode_next(self, obj):
        tobj = type(obj)
        if tobj in self.dispatch:
            res = self.dispatch[tobj](self, obj)
        else:
            return self.encode_next(self._default(obj))
        if isinstance(res, bytes):
            return res
        return bytes().join(res)

    def encode_noop(self, obj):
        return NOOP
    dispatch[type(NOOP_SENTINEL)] = encode_noop

    def encode_none(self, obj):
        return NULL
    dispatch[type(None)] = encode_none

    def encode_bool(self, obj):
        return TRUE if obj else FALSE
    dispatch[bool] = encode_bool

    def encode_int(self, obj):
        if (-2 ** 7) <= obj <= (2 ** 7 - 1):
            return INT8 + CHARS[obj % 256]
        elif 0 <= obj <= 255:
            return UINT8 + CHARS[obj]
        elif (-2 ** 15) <= obj <= (2 ** 15 - 1):
            return INT16 + pack('>h', obj)
        elif (-2 ** 31) <= obj <= (2 ** 31 - 1):
            return INT32 + pack('>i', obj)
        #elif (-2 ** 63) <= obj <= (2 ** 63 - 1):
        else:
            return INT64 + pack('>q', obj)
        #else:
        #    return self.encode_decimal(Decimal(obj))
    dispatch[int] = encode_int
    dispatch[long] = encode_int

    def encode_float(self, obj):
        if isinf(obj) or isnan(obj):
            return NULL
        elif 1.18e-38 <= abs(obj) <= 3.4e38:
            return FLOAT + pack('>f', obj)
        #elif 2.23e-308 <= abs(obj) < 1.8e308:
        else:
            return DOUBLE + pack('>d', obj)
        #elif isinf(obj) or isnan(obj):
        #    return NULL
        #else:
        #    return self.encode_decimal(Decimal(obj))
    dispatch[float] = encode_float

    def _encode_str(self, obj):
        length = len(obj)
        if length == 1:
            return CHAR + obj
        elif length <= 127:
            return STRING + INT8 + CHARS[length] + obj
        elif length <= 255:
            return STRING + UINT8 + CHARS[length] + obj
        return STRING + self.encode_int(length) + obj

    def encode_bytes(self, obj): 
        try:
            obj.decode('utf-8')
        except UnicodeDecodeError:
            raise EncodeError('Invalid UTF-8 byte string: %r' % obj)
        else:
            return self._encode_str(obj)
    dispatch[bytes] = encode_bytes

    def encode_str(self, obj):
        return self._encode_str(obj.encode('utf-8'))
    dispatch[unicode] = encode_str

    def encode_decimal(self, obj):
        obj = unicode(obj).encode('utf-8')
        return HIDEF + self.encode_int(len(obj)) + obj
    dispatch[Decimal] = encode_decimal

    def encode_sequence(self, obj):
        yield ARRAY_OPEN
        for item in obj:
            yield self.encode_next(item)
        yield ARRAY_CLOSE
    dispatch[tuple] = encode_sequence
    dispatch[list] = encode_sequence
    dispatch[type((i for i in ()))] = encode_sequence
    dispatch[set] = encode_sequence
    dispatch[frozenset] = encode_sequence
    dispatch[xrange] = encode_sequence
    dispatch[dict_keysiterator] = encode_sequence
    dispatch[dict_valuesiterator] = encode_sequence

    def encode_dict(self, obj):
        yield OBJECT_OPEN
        if isinstance(obj, dict):
            items = obj.items()
        else:
            items = obj
        for key, value in items:
            if isinstance(key, unicode):
                yield self.encode_str(key)
            elif isinstance(key, bytes):
                yield self.encode_bytes(key)
            else:
                raise EncodeError('invalid object key %r' % key)
            yield self.encode_next(value)
        yield OBJECT_CLOSE
    dispatch[dict] = encode_dict
    dispatch[dict_itemsiterator] = encode_dict
