# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2014 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution.
#

# <pep8 compliant>

__version_info__ = (0, 7, 0, '', 0)
__version__ = '%(version)s%(tag)s%(build)s' % {
    'version': '.'.join(map(str, __version_info__[:3])),
    'tag': '-' + __version_info__[3] if __version_info__[3] else '',
    'build': '.' + str(__version_info__[4]) if __version_info__[4] else ''
}
