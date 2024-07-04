# -*- coding: utf-8 -*-

"""The illumio library provides a simple interface for interacting with PCE APIs.

Copyright:
    © 2022 Illumio

License:
    Apache2, see LICENSE for more details.
"""
from .exceptions import *
from .secpolicy import *
from .util import *
from .policyobjects import *
from .cs2 import *

from types import ModuleType

# avoid name conflicts with package modules when using
# `from illumio import *` by excluding them here
__all__ = [
    export for export, o in globals().items()
        if not (export.startswith('_') or isinstance(o, ModuleType))
]
