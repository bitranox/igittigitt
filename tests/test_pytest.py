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
def parser_test_comments():
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('somematch', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('#realcomment', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('othermatch', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('\\#imnocomment', base_path=pathlib.Path('/home/michael'))
    return ignore_parser


@pytest.fixture(scope='function')
def parser_test_wildcard():
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('hello.*', base_path=pathlib.Path('/home/michael'))
    return ignore_parser


@pytest.fixture(scope='function')
def parser_test_anchored_wildcard():
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('/hello.*', base_path=pathlib.Path('/home/michael'))
    return ignore_parser


@pytest.fixture(scope='function')
def parser_test_trailing_spaces():
    """
    is that really necessary ? Because there should be no files to filter
    with a trailing space on the filesystem ?

    """
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('ignoretrailingspace ', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('notignoredspace\\ ', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('partiallyignoredspace\\  ', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('partiallyignoredspace2 \\  ', base_path=pathlib.Path('/home/michael'))
    ignore_parser.add_rule('notignoredmultiplespace\\ \\ \\ ', base_path=pathlib.Path('/home/michael'))
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

    assert not parser_simple_git_rules.match('/home/michael/main.py')
    assert not parser_simple_git_rules.match('/home/bitranox/main.py')
    assert parser_simple_git_rules.match('/home/michael/main.pyc')
    assert parser_simple_git_rules.match('/home/michael/dir/main.pyc')
    assert parser_simple_git_rules.match('/home/michael/__pycache__')
    assert parser_simple_git_rules.match('/home/michael/.venv/')
    assert parser_simple_git_rules.match('/home/michael/.venv/folder')
    assert parser_simple_git_rules.match('/home/michael/.venv/file.txt')


def test_comments(parser_test_comments):
    assert parser_test_comments.match(pathlib.Path('/home/michael/somematch'))
    assert not parser_test_comments.match(pathlib.Path('/home/michael/#realcomment'))
    assert parser_test_comments.match(pathlib.Path('/home/michael/othermatch'))
    assert parser_test_comments.match(pathlib.Path('/home/michael/#imnocomment'))

    assert parser_test_comments.match('/home/michael/somematch')
    assert not parser_test_comments.match('/home/michael/#realcomment')
    assert parser_test_comments.match('/home/michael/othermatch')
    assert parser_test_comments.match('/home/michael/#imnocomment')


def test_wildcard(parser_test_wildcard):
    assert parser_test_wildcard.match(pathlib.Path('/home/michael/hello.txt'))
    assert parser_test_wildcard.match(pathlib.Path('/home/michael/hello.foobar/'))
    assert parser_test_wildcard.match(pathlib.Path('/home/michael/dir/hello.txt'))
    assert parser_test_wildcard.match(pathlib.Path('/home/michael/hello.'))
    assert not parser_test_wildcard.match(pathlib.Path('/home/michael/hello'))
    assert not parser_test_wildcard.match(pathlib.Path('/home/michael/helloX'))

    assert parser_test_wildcard.match('/home/michael/hello.txt')
    assert parser_test_wildcard.match('/home/michael/hello.foobar/')
    assert parser_test_wildcard.match('/home/michael/dir/hello.txt')
    assert parser_test_wildcard.match('/home/michael/hello.')
    assert not parser_test_wildcard.match('/home/michael/hello')
    assert not parser_test_wildcard.match('/home/michael/helloX')


def test_anchored_wildcard(parser_test_anchored_wildcard):
    assert parser_test_anchored_wildcard.match(pathlib.Path('/home/michael/hello.txt'))
    assert parser_test_anchored_wildcard.match(pathlib.Path('/home/michael/hello.c'))
    assert not parser_test_anchored_wildcard.match(pathlib.Path('/home/michael/a/hello.java'))

    assert parser_test_anchored_wildcard.match('/home/michael/hello.txt')
    assert parser_test_anchored_wildcard.match('/home/michael/hello.c')
    assert not parser_test_anchored_wildcard.match('/home/michael/a/hello.java')


def test_trailing_spaces(parser_test_trailing_spaces):
    """
    is that really necessary ? Because there should be no files to filter
    with a trailing space on the filesystem ?

    """
    assert parser_test_trailing_spaces.match('/home/michael/ignoretrailingspace')
    assert not parser_test_trailing_spaces.match('/home/michael/ignoretrailingspace ')

    assert parser_test_trailing_spaces.match('/home/michael/partiallyignoredspace ')
    assert not parser_test_trailing_spaces.match('/home/michael/partiallyignoredspace  ')
    assert not parser_test_trailing_spaces.match('/home/michael/partiallyignoredspace')

    assert parser_test_trailing_spaces.match('/home/michael/partiallyignoredspace2  ')
    assert not parser_test_trailing_spaces.match('/home/michael/partiallyignoredspace2   ')
    assert not parser_test_trailing_spaces.match('/home/michael/partiallyignoredspace2 ')
    assert not parser_test_trailing_spaces.match('/home/michael/partiallyignoredspace2')

    assert parser_test_trailing_spaces.match('/home/michael/notignoredspace ')
    assert not parser_test_trailing_spaces.match('/home/michael/notignoredspace')

    assert parser_test_trailing_spaces.match('/home/michael/notignoredmultiplespace   ')
    assert not parser_test_trailing_spaces.match('/home/michael/notignoredmultiplespace')


def test_negation_rules(parser_negation_git_rules):
    assert parser_negation_git_rules.match(pathlib.Path('/home/michael/trash.ignore'))
    assert parser_negation_git_rules.match(pathlib.Path('/home/michael/whatever.ignore'))
    assert not parser_negation_git_rules.match(pathlib.Path('/home/michael/keep.ignore'))
    assert not parser_negation_git_rules.match(pathlib.Path('/home/bitranox/keep.ignore'))

    assert parser_negation_git_rules.match('/home/michael/trash.ignore')
    assert parser_negation_git_rules.match('/home/michael/whatever.ignore')
    assert not parser_negation_git_rules.match('/home/michael/keep.ignore')
    assert not parser_negation_git_rules.match('/home/bitranox/keep.ignore')


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
