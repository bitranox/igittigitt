# detect test environment and add path for local testing
# this should be the first import in __init__.py
from lib_detect_testenv import *

if is_testenv_active():
    add_path_to_syspath(__file__)

# put Your imports here
from .conf_igittigitt import conf_igittigitt
from .igittigitt import *

# __init__conf__ needs to be imported after Your imports, otherwise we would create circular import on the cli script,
# which is reading some values from __init__conf__
from . import __init__conf__

__title__ = __init__conf__.title
__version__ = __init__conf__.version
__name__ = __init__conf__.name
__url__ = __init__conf__.url
__author__ = __init__conf__.author
__author_email__ = __init__conf__.author_email

__all__ = ["conf_igittigitt", "IgnoreParser"]
