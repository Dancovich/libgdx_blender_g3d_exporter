# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2014 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution.
#

# <pep8 compliant>

class DecodeError(ValueError):
    """UBJSON data decoding error."""


class MarkerError(DecodeError):
    """Raises if unknown or invalid marker was found in decoded data stream."""


class EarlyEndOfStreamError(DecodeError):
    """Raises when data stream unexpectedly ends."""


class EncodeError(TypeError):
    """Python object encoding error."""
