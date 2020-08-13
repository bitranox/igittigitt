# STDLIB
from tempfile import NamedTemporaryFile
import os
import pathlib
import pytest
from unittest import TestCase

# PROJ
import igittigitt


@pytest.fixture(scope='function')
def simple_git_rules():
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('__pycache__', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('*.py[cod]', base_path=pathlib.Path('/home/michael'))
    return ignore_parser


@pytest.fixture(scope='function')
def negation_git_rules():
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('*.ignore', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('!keep.ignore', base_path=pathlib.Path('/home/michael'))
    return ignore_parser


def test_simple_rules(simple_git_rules: igittigitt.IgnoreParser):
    assert not simple_git_rules.match(pathlib.Path('/home/michael/main.py'))
    assert not simple_git_rules.match(pathlib.Path('/home/bitranox/main.py'))
    assert simple_git_rules.match(pathlib.Path('/home/michael/main.pyc'))
    assert simple_git_rules.match(pathlib.Path('/home/michael/dir/main.pyc'))
    assert simple_git_rules.match(pathlib.Path('/home/michael/__pycache__'))


def test_negation_rules(negation_git_rules: igittigitt.IgnoreParser):
    assert negation_git_rules.match(pathlib.Path('/home/michael/trash.ignore'))
    assert negation_git_rules.match(pathlib.Path('/home/michael/keep.ignore'))
    assert not negation_git_rules.match(pathlib.Path('/home/michael/keep.ignore'))
    assert not negation_git_rules.match(pathlib.Path('/home/bitranox/keep.ignore'))


def doctest_examples():
    """

    >>> # EXAMPLE IgnoreParser Instance
    # IgnoreParserExamples{{{

    >>> # init as normal Instance
    >>> parser = igittigitt.IgnoreParser()
    >>> print(parser)
    <...IgnoreParser object at ...>

    >>> # init with context manager
    >>> with igittigitt.IgnoreParser() as parser:
    ...     print(parser)
    <...IgnoreParser object at ...>

    # IgnoreParserExamples}}}

    """
    pass
