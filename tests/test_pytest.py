# STDLIB
import pathlib
import platform
import pytest

# PROJ
import igittigitt


@pytest.fixture(scope='function')
def base_path():
    if platform.system() == 'Windows':
        return pathlib.Path('C:/Users/michael').resolve()
    else:
        return pathlib.Path('/home/michael').resolve()


@pytest.fixture(scope='function')
def parser_simple_git_rules(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    # add rules with base path as pathlib.Path
    ignore_parser.add_rule('__pycache__', base_path=base_path)
    ignore_parser.add_rule('*.py[cod]', base_path=base_path)
    ignore_parser.add_rule('.venv/', base_path=base_path)
    # add rules with base path as string
    ignore_parser.add_rule('__pycache__', base_path=str(base_path))
    ignore_parser.add_rule('*.py[cod]', base_path=str(base_path))
    ignore_parser.add_rule('.venv/', base_path=str(base_path))

    return ignore_parser


@pytest.fixture(scope='function')
def parser_test_comments(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('somematch', base_path=base_path)
    ignore_parser.add_rule('#realcomment', base_path=base_path)
    ignore_parser.add_rule('othermatch', base_path=base_path)
    ignore_parser.add_rule('\\#imnocomment', base_path=base_path)
    return ignore_parser


@pytest.fixture(scope='function')
def parser_test_wildcard(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('hello.*', base_path=base_path)
    return ignore_parser


@pytest.fixture(scope='function')
def parser_test_anchored_wildcard(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('/hello.*', base_path=base_path)
    return ignore_parser


@pytest.fixture(scope='function')
def parser_test_trailing_spaces(base_path):
    """
    is that really necessary ? Because there should be no files to filter
    with a trailing space on the filesystem ?

    """
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('ignoretrailingspace ', base_path=base_path)
    ignore_parser.add_rule('notignoredspace\\ ', base_path=base_path)
    ignore_parser.add_rule('partiallyignoredspace\\  ', base_path=base_path)
    ignore_parser.add_rule('partiallyignoredspace2 \\  ', base_path=base_path)
    ignore_parser.add_rule('notignoredmultiplespace\\ \\ \\ ', base_path=base_path)
    return ignore_parser


@pytest.fixture(scope='function')
def parser_negation_git_rules(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule('*.ignore', base_path=base_path)
    ignore_parser.add_rule('!keep.ignore', base_path=base_path)
    return ignore_parser


def test_simple_rules(parser_simple_git_rules, base_path):
    assert not parser_simple_git_rules.match(base_path / 'main.py')
    # test a path that is outside of the base path
    assert not parser_simple_git_rules.match(base_path.parent / 'bitranox/main.py')
    assert parser_simple_git_rules.match(base_path / 'main.pyc')
    assert parser_simple_git_rules.match(base_path / 'dir/main.pyc')
    assert parser_simple_git_rules.match(base_path / '__pycache__')
    assert parser_simple_git_rules.match(base_path / '.venv/')
    assert parser_simple_git_rules.match(base_path / '.venv/folder')
    assert parser_simple_git_rules.match(base_path / '.venv/file.txt')

    assert not parser_simple_git_rules.match(str(base_path) + '/main.py')
    assert not parser_simple_git_rules.match(str(base_path.parent) + '/bitranox/main.py')
    assert parser_simple_git_rules.match(str(base_path) + '/main.pyc')
    assert parser_simple_git_rules.match(str(base_path) + '/dir/main.pyc')
    assert parser_simple_git_rules.match(str(base_path) + '/__pycache__')
    assert parser_simple_git_rules.match(str(base_path) + '/.venv/')
    assert parser_simple_git_rules.match(str(base_path) + '/.venv/folder')
    assert parser_simple_git_rules.match(str(base_path) + '/.venv/file.txt')


def test_comments(parser_test_comments, base_path):
    assert parser_test_comments.match(base_path / 'somematch')
    assert not parser_test_comments.match(base_path / '#realcomment')
    assert parser_test_comments.match(base_path / 'othermatch')
    assert parser_test_comments.match(base_path / '#imnocomment')

    assert parser_test_comments.match(str(base_path) + '/somematch')
    assert not parser_test_comments.match(str(base_path) + '/#realcomment')
    assert parser_test_comments.match(str(base_path) + '/othermatch')
    assert parser_test_comments.match(str(base_path) + '/#imnocomment')


def test_wildcard(parser_test_wildcard, base_path):
    assert parser_test_wildcard.match(base_path / 'hello.txt')
    assert parser_test_wildcard.match(base_path / 'hello.foobar/')
    assert parser_test_wildcard.match(base_path / 'dir/hello.txt')
    assert parser_test_wildcard.match(base_path / 'hello.')
    assert not parser_test_wildcard.match(base_path / 'hello')
    assert not parser_test_wildcard.match(base_path / 'helloX')

    assert parser_test_wildcard.match(str(base_path) + '/hello.txt')
    assert parser_test_wildcard.match(str(base_path) + '/hello.foobar/')
    assert parser_test_wildcard.match(str(base_path) + '/dir/hello.txt')
    assert parser_test_wildcard.match(str(base_path) + '/hello.')
    assert not parser_test_wildcard.match(str(base_path) + '/hello')
    assert not parser_test_wildcard.match(str(base_path) + '/helloX')


def test_anchored_wildcard(parser_test_anchored_wildcard, base_path):
    assert parser_test_anchored_wildcard.match(base_path / 'hello.txt')
    assert parser_test_anchored_wildcard.match(base_path / 'hello.c')
    assert not parser_test_anchored_wildcard.match(base_path / 'a/hello.java')

    assert parser_test_anchored_wildcard.match(str(base_path) + '/hello.txt')
    assert parser_test_anchored_wildcard.match(str(base_path) + '/hello.c')
    assert not parser_test_anchored_wildcard.match(str(base_path) + '/a/hello.java')


def test_trailing_spaces(parser_test_trailing_spaces, base_path):
    """
    is that really necessary ? Because there should be no files to filter
    with a trailing space on the filesystem ?

    """
    assert parser_test_trailing_spaces.match(str(base_path) + '/ignoretrailingspace')
    assert not parser_test_trailing_spaces.match(str(base_path) + '/ignoretrailingspace ')

    assert parser_test_trailing_spaces.match(str(base_path) + '/partiallyignoredspace ')
    assert not parser_test_trailing_spaces.match(str(base_path) + '/partiallyignoredspace  ')
    assert not parser_test_trailing_spaces.match(str(base_path) + '/partiallyignoredspace')

    assert parser_test_trailing_spaces.match(str(base_path) + '/partiallyignoredspace2  ')
    assert not parser_test_trailing_spaces.match(str(base_path) + '/partiallyignoredspace2   ')
    assert not parser_test_trailing_spaces.match(str(base_path) + '/partiallyignoredspace2 ')
    assert not parser_test_trailing_spaces.match(str(base_path) + '/partiallyignoredspace2')

    assert parser_test_trailing_spaces.match(str(base_path) + '/notignoredspace ')
    assert not parser_test_trailing_spaces.match(str(base_path) + '/notignoredspace')

    assert parser_test_trailing_spaces.match(str(base_path) + '/notignoredmultiplespace   ')
    assert not parser_test_trailing_spaces.match(str(base_path) + '/notignoredmultiplespace')


def test_negation_rules(parser_negation_git_rules, base_path):
    assert parser_negation_git_rules.match(base_path / 'trash.ignore')
    assert parser_negation_git_rules.match(base_path / 'whatever.ignore')
    assert not parser_negation_git_rules.match(base_path / 'keep.ignore')
    assert not parser_negation_git_rules.match(base_path.parent / 'bitranox/keep.ignore')

    assert parser_negation_git_rules.match(str(base_path) + '/trash.ignore')
    assert parser_negation_git_rules.match(str(base_path) + '/whatever.ignore')
    assert not parser_negation_git_rules.match(str(base_path) + '/keep.ignore')
    assert not parser_negation_git_rules.match(str(base_path.parent) + '/bitranox/keep.ignore')


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

    # add_rule_Example{{{
    >>> parser = igittigitt.IgnoreParser()
    >>> parser.add_rule('*.py[cod]', base_path='/home/michael')

    # add_rule_Example}}}


    """
    pass


if __name__ == '__main__':
    pytest.main(['--log-cli-level', 'ERROR'])
