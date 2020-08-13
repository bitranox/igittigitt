# STDLIB
import pathlib
import pytest

# PROJ
import igittigitt


@pytest.fixture(scope='function')
def parser_simple_git_rules():
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('__pycache__', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('*.py[cod]', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('.venv/', base_path=pathlib.Path('/home/michael'))
    return ignore_parser


@pytest.fixture(scope='function')
def parser_negation_git_rules():
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('*.ignore', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('!keep.ignore', base_path=pathlib.Path('/home/michael'))
    return ignore_parser


def test_simple_rules(parser_simple_git_rules):
    assert not parser_simple_git_rules.match(pathlib.Path('/home/michael/main.py'))
    assert not parser_simple_git_rules.match(pathlib.Path('/home/bitranox/main.py'))
    assert parser_simple_git_rules.match(pathlib.Path('/home/michael/main.pyc'))
    assert parser_simple_git_rules.match(pathlib.Path('/home/michael/dir/main.pyc'))
    assert parser_simple_git_rules.match(pathlib.Path('/home/michael/__pycache__'))
    assert parser_simple_git_rules.match(pathlib.Path('/home/michael/.venv/'))
    assert parser_simple_git_rules.match(pathlib.Path('/home/michael/.venv/folder'))
    assert parser_simple_git_rules.match(pathlib.Path('/home/michael/.venv/file.txt'))


def test_negation_rules(parser_negation_git_rules):
    assert parser_negation_git_rules.match(pathlib.Path('/home/michael/trash.ignore'))
    assert parser_negation_git_rules.match(pathlib.Path('/home/michael/whatever.ignore'))
    assert not parser_negation_git_rules.match(pathlib.Path('/home/michael/keep.ignore'))
    assert not parser_negation_git_rules.match(pathlib.Path('/home/bitranox/keep.ignore'))


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


if __name__ == '__main__':
    pytest.main(['--log-cli-level', 'ERROR'])
