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
# from ..draft8 import Draft8Decoder
from ..draft9 import Draft9Decoder
from ..exceptions import EarlyEndOfStreamError
import io_scene_g3d

output_old_format = True

def pprint(data, output=sys.stdout, allow_noop=True,
           indent=' ' * 4, max_level=None, spec='draft-9'):
    """Pretty prints ubjson data using the handy [ ]-notation to represent it in
    readable form. Example::

        [{]
            [S] [i] [2] [id]
            [I] [1234567890]
            [S] [i] [4] [name]
            [S] [i] [3] [bob]
        [}]

    :param data: `.read([size])`-able object or source string with ubjson data.
    :param output: `.write([data])`-able object.
    :param allow_noop: Allow emit :const:`~simpleubjson.NOOP` or not.
    :param indent: Indention string.
    :param max_level: Max level of inspection nested containers. By default
                      there is no limit, but you may hit system recursion limit.
    :param spec: UBJSON specification. Supported Draft-8 and Draft-9
                 specifications by ``draft-8`` or ``draft-9`` keys.
    :type spec: str
    """
    def maybe_write(data, level):
        if max_level is None or level <= max_level:
            output.write('%s' % (indent * level))
            output.write(data)
            output.flush()

    def inspect_draft9(decoder, level, *args):
        while 1:
            try:
                tag, length, value = decoder.next_tlv()
                utag = tag.decode()
            except EarlyEndOfStreamError:
                break
            # standalone markers
            if length is None and value is None:
                if utag in ']}':
                    level -= 1
                maybe_write('[%s]\n' % (utag,), level)
                if utag in '{[':
                    level += 1

            # plane values
            elif length is None and value is not None:
                value = decoder.dispatch[tag](decoder, tag, length, value)
                maybe_write('[%s] [%s]\n' % (utag, value), level)

            # sized values
            else:
                value = decoder.dispatch[tag](decoder, tag, length, value)
                pattern = '[%s] [%s] [%s] [%s]\n'
                # very dirty hack to show size as marker and value
                _decoder = Draft9Decoder(io_scene_g3d.simpleubjson.encode(length, spec=spec))
                _decoder.old_format_json = output_old_format
                tlv = _decoder.next_tlv()
                args = tuple([utag, tlv[0].decode(), tlv[2], value])
                maybe_write(pattern % args, level)

    # if spec.lower() in ['draft8', 'draft-8']:
        # decoder = Draft8Decoder(data, allow_noop)
        # inspect = inspect_draft8
    # elif spec.lower() in ['draft9', 'draft-9']:
    if spec.lower() in ['draft9', 'draft-9']:
        decoder = Draft9Decoder(data, allow_noop)
        decoder.old_format_json = output_old_format
        inspect = inspect_draft9
    else:
        raise ValueError('Unknown or unsupported specification %s' % spec)

    inspect(decoder, 0, 255)
