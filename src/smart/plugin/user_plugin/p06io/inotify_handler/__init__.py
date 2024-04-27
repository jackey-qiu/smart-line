from __future__ import absolute_import

try:
    from .inotify_handler import *
except ImportError as err:
    print(err)
