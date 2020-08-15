# STDLIB
import pathlib
import platform
import pytest
import shutil

# PROJ
import igittigitt


@pytest.fixture(scope="function")
def base_path():
    if platform.system() == "Windows":
        return pathlib.Path("C:/Users/bitranox").resolve()
    else:
        return pathlib.Path("/home/bitranox").resolve()


@pytest.fixture(scope="function")
def parser_simple_git_rules(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    # add rules with base path as pathlib.Path
    ignore_parser.add_rule("__pycache__", base_path=base_path)
    ignore_parser.add_rule("*.py[cod]", base_path=base_path)
    ignore_parser.add_rule(".venv/", base_path=base_path)
    # add rules with base path as string
    ignore_parser.add_rule("__pycache__", base_path=str(base_path))
    ignore_parser.add_rule("*.py[cod]", base_path=str(base_path))
    ignore_parser.add_rule(".venv/", base_path=str(base_path))

    return ignore_parser


@pytest.fixture(scope="function")
def parser_test_comments(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule("somematch", base_path=base_path)
    ignore_parser.add_rule("#realcomment", base_path=base_path)
    ignore_parser.add_rule("othermatch", base_path=base_path)
    ignore_parser.add_rule("\\#imnocomment", base_path=base_path)
    return ignore_parser


@pytest.fixture(scope="function")
def parser_test_wildcard(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule("hello.*", base_path=base_path)
    return ignore_parser


@pytest.fixture(scope="function")
def parser_test_anchored_wildcard(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule("/hello.*", base_path=base_path)
    return ignore_parser


@pytest.fixture(scope="function")
def parser_negation_git_rules(base_path):
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule("*.ignore", base_path=base_path)
    ignore_parser.add_rule("!keep.ignore", base_path=base_path)
    return ignore_parser


def test_simple_rules(parser_simple_git_rules, base_path):
    assert not parser_simple_git_rules.match(base_path / "main.py")
    # test a path that is outside of the base path
    assert not parser_simple_git_rules.match(base_path.parent / "bitranox/main.py")
    assert parser_simple_git_rules.match(base_path / "main.pyc")
    assert parser_simple_git_rules.match(base_path / "dir/main.pyc")
    assert parser_simple_git_rules.match(base_path / "__pycache__")
    assert parser_simple_git_rules.match(base_path / ".venv/")
    assert parser_simple_git_rules.match(base_path / ".venv/folder")
    assert parser_simple_git_rules.match(base_path / ".venv/file.txt")

    assert not parser_simple_git_rules.match(str(base_path) + "/main.py")
    assert not parser_simple_git_rules.match(
        str(base_path.parent) + "/bitranox/main.py"
    )
    assert parser_simple_git_rules.match(str(base_path) + "/main.pyc")
    assert parser_simple_git_rules.match(str(base_path) + "/dir/main.pyc")
    assert parser_simple_git_rules.match(str(base_path) + "/__pycache__")
    assert parser_simple_git_rules.match(str(base_path) + "/.venv/")
    assert parser_simple_git_rules.match(str(base_path) + "/.venv/folder")
    assert parser_simple_git_rules.match(str(base_path) + "/.venv/file.txt")


def test_comments(parser_test_comments, base_path):
    assert parser_test_comments.match(base_path / "somematch")
    assert not parser_test_comments.match(base_path / "#realcomment")
    assert parser_test_comments.match(base_path / "othermatch")
    assert parser_test_comments.match(base_path / "#imnocomment")

    assert parser_test_comments.match(str(base_path) + "/somematch")
    assert not parser_test_comments.match(str(base_path) + "/#realcomment")
    assert parser_test_comments.match(str(base_path) + "/othermatch")
    assert parser_test_comments.match(str(base_path) + "/#imnocomment")


def test_wildcard(parser_test_wildcard, base_path):
    assert parser_test_wildcard.match(base_path / "hello.txt")
    assert parser_test_wildcard.match(base_path / "hello.foobar/")
    assert parser_test_wildcard.match(base_path / "dir/hello.txt")
    assert parser_test_wildcard.match(base_path / "hello.")
    assert not parser_test_wildcard.match(base_path / "hello")
    assert not parser_test_wildcard.match(base_path / "helloX")

    assert parser_test_wildcard.match(str(base_path) + "/hello.txt")
    assert parser_test_wildcard.match(str(base_path) + "/hello.foobar/")
    assert parser_test_wildcard.match(str(base_path) + "/dir/hello.txt")
    assert parser_test_wildcard.match(str(base_path) + "/hello.")
    assert not parser_test_wildcard.match(str(base_path) + "/hello")
    assert not parser_test_wildcard.match(str(base_path) + "/helloX")


def test_anchored_wildcard(parser_test_anchored_wildcard, base_path):
    assert parser_test_anchored_wildcard.match(base_path / "hello.txt")
    assert parser_test_anchored_wildcard.match(base_path / "hello.c")
    assert not parser_test_anchored_wildcard.match(base_path / "a/hello.java")

    assert parser_test_anchored_wildcard.match(str(base_path) + "/hello.txt")
    assert parser_test_anchored_wildcard.match(str(base_path) + "/hello.c")
    assert not parser_test_anchored_wildcard.match(str(base_path) + "/a/hello.java")


def test_negation_rules(parser_negation_git_rules, base_path):
    assert parser_negation_git_rules.match(base_path / "trash.ignore")
    assert parser_negation_git_rules.match(base_path / "whatever.ignore")
    assert not parser_negation_git_rules.match(base_path / "keep.ignore")
    assert not parser_negation_git_rules.match(
        base_path.parent / "bitranox/keep.ignore"
    )

    assert parser_negation_git_rules.match(str(base_path) + "/trash.ignore")
    assert parser_negation_git_rules.match(str(base_path) + "/whatever.ignore")
    assert not parser_negation_git_rules.match(str(base_path) + "/keep.ignore")
    assert not parser_negation_git_rules.match(
        str(base_path.parent) + "/bitranox/keep.ignore"
    )


def test_parse_rule_files():
    path_test_dir = pathlib.Path(__file__).parent.resolve() / "example"
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.parse_rule_files(base_dir=path_test_dir, filename=".test_gitignore")
    paths_unfiltered = path_test_dir.glob("**/*")
    paths_filtered = list()
    for path in paths_unfiltered:
        if not ignore_parser.match(path):
            paths_filtered.append(path.name)
    assert sorted(paths_filtered) == [
        ".test_gitignore",
        ".test_gitignore",
        "excluded_not",
        "excluded_not.txt",
        "not_excluded",
        "not_excluded.txt",
        "not_excluded2",
        "not_excluded2.txt",
        "some_file.txt",
    ]


def test_shutil_ignore_function():
    """
    >>> test_shutil_ignore_function()

    """
    # Setup
    path_test_dir = pathlib.Path(__file__).parent.resolve()

    path_source_dir = path_test_dir / "example"
    path_target_dir = path_test_dir / "target"
    shutil.rmtree(path_target_dir, ignore_errors=True)

    # Test
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.parse_rule_files(base_dir=path_source_dir, filename=".test_gitignore")
    shutil.copytree(
        path_source_dir, path_target_dir, ignore=ignore_parser.shutil_ignore,
    )

    assert len(list(path_target_dir.glob("**/*"))) == 8

    # Teardown
    shutil.rmtree(path_target_dir, ignore_errors=True)


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
    >>> parser.add_rule('*.py[cod]', base_path='/home/bitranox')

    # add_rule_Example}}}


    >>> path_test_dir = pathlib.Path(__file__).parent.resolve()
    >>> path_target_dir = path_test_dir / "target"
    >>> shutil.rmtree(path_target_dir, ignore_errors=True)

    # test_shutil_ignore_function_Example{{{
    >>> path_source_dir = path_test_dir / "example"
    >>> path_target_dir = path_test_dir / "target"
    >>> ignore_parser = igittigitt.IgnoreParser()
    >>> ignore_parser.parse_rule_files(base_dir=path_source_dir, filename=".test_gitignore")
    >>> shutil.copytree(path_source_dir, path_target_dir, ignore=ignore_parser.shutil_ignore)

    # test_shutil_ignore_function_Example}}}
    # Teardown
    >>> shutil.rmtree(path_target_dir, ignore_errors=True)







    """
    pass


if __name__ == "__main__":
    pytest.main(["--log-cli-level", "ERROR"])
