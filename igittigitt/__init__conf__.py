# STDLIB
import os
import sys

name = "igittigitt"
title = "A spec-compliant gitignore parser for Python"
version = "v2.0.6b"
url = "https://github.com/bitranox/igittigitt"
author = "Robert Nowotny"
author_email = "bitranox@gmail.com"
shell_command = "igittigitt"


def print_info() -> None:
    print(
        """\

Info for igittigitt:

    A spec-compliant gitignore parser for Python

    Version : v2.0.6b
    Url     : https://github.com/bitranox/igittigitt
    Author  : Robert Nowotny
    Email   : bitranox@gmail.com"""
    )


def is_doctest_running() -> bool:
    """
    >>> if not is_setup_test_running(): assert is_doctest_running() == True
    """
    # this is used in our tests when we test cli-commands
    if os.getenv("PYTEST_IS_RUNNING"):
        return True

    for argv in sys.argv:
        if is_doctest_in_arg_string(argv):
            return True
    return False


def is_setup_test_running() -> bool:
    """if 'setup.py test' was launched"""
    for arg_string in sys.argv:
        if "setup.py" in arg_string:
            return True
    return False


def is_doctest_in_arg_string(arg_string: str) -> bool:
    """
    >>> assert is_doctest_in_arg_string('test') == False
    >>> assert is_doctest_in_arg_string('test/docrunner.py::::test')
    >>> assert is_doctest_in_arg_string('test/pytest.py::::test')
    """
    arg_string = arg_string.replace("\\", "/")
    if ("docrunner.py" in arg_string) or ("pytest.py" in arg_string) or ("/pytest/__main__.py" in arg_string):
        return True
    else:
        return False
