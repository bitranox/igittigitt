# STDLIB
import pathlib
import platform
import pytest
import shutil
import sys

# PROJ
import igittigitt


@pytest.fixture(scope="function")
def base_path() -> pathlib.Path:
    if platform.system() == "Windows":
        return pathlib.Path("C:/Users/bitranox").resolve()
    else:
        return pathlib.Path("/home/bitranox").resolve()


@pytest.fixture(scope="function")
def parser_simple_git_rules(base_path: pathlib.Path) -> igittigitt.IgnoreParser:
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
def parser_test_comments(base_path: pathlib.Path) -> igittigitt.IgnoreParser:
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule("somematch", base_path=base_path)
    ignore_parser.add_rule("#realcomment", base_path=base_path)
    ignore_parser.add_rule("othermatch", base_path=base_path)
    ignore_parser.add_rule("\\#imnocomment", base_path=base_path)
    return ignore_parser


@pytest.fixture(scope="function")
def parser_test_wildcard(base_path: pathlib.Path) -> igittigitt.IgnoreParser:
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule("hello.*", base_path=base_path)
    return ignore_parser


@pytest.fixture(scope="function")
def parser_test_anchored_wildcard(base_path: pathlib.Path) -> igittigitt.IgnoreParser:
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule("/hello.*", base_path=base_path)
    return ignore_parser


@pytest.fixture(scope="function")
def parser_negation_git_rules(base_path: pathlib.Path) -> igittigitt.IgnoreParser:
    ignore_parser = igittigitt.IgnoreParser()
    ignore_parser.add_rule("*.ignore", base_path=base_path)
    ignore_parser.add_rule("!keep.ignore", base_path=base_path)
    return ignore_parser


def test_simple_rules(parser_simple_git_rules: igittigitt.IgnoreParser, base_path: pathlib.Path) -> None:
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
    assert not parser_simple_git_rules.match(str(base_path.parent) + "/bitranox/main.py")
    assert parser_simple_git_rules.match(str(base_path) + "/main.pyc")
    assert parser_simple_git_rules.match(str(base_path) + "/dir/main.pyc")
    assert parser_simple_git_rules.match(str(base_path) + "/__pycache__")
    assert parser_simple_git_rules.match(str(base_path) + "/.venv/")
    assert parser_simple_git_rules.match(str(base_path) + "/.venv/folder")
    assert parser_simple_git_rules.match(str(base_path) + "/.venv/file.txt")


def test_comments(parser_test_comments: igittigitt.IgnoreParser, base_path: pathlib.Path) -> None:
    assert parser_test_comments.match(base_path / "somematch")
    assert not parser_test_comments.match(base_path / "#realcomment")
    assert parser_test_comments.match(base_path / "othermatch")
    assert parser_test_comments.match(base_path / "#imnocomment")

    assert parser_test_comments.match(str(base_path) + "/somematch")
    assert not parser_test_comments.match(str(base_path) + "/#realcomment")
    assert parser_test_comments.match(str(base_path) + "/othermatch")
    assert parser_test_comments.match(str(base_path) + "/#imnocomment")


def test_wildcard(parser_test_wildcard: igittigitt.IgnoreParser, base_path: pathlib.Path) -> None:
    assert parser_test_wildcard.match(base_path / "hello.txt")
    assert parser_test_wildcard.match(base_path / "hello.foobar/")
    assert parser_test_wildcard.match(base_path / "dir/hello.txt")

    if platform.system() == "Windows":
        # in Windows there can be no files ending with a point
        assert not parser_test_wildcard.match(base_path / "hello.")
    else:
        assert parser_test_wildcard.match(base_path / "hello.")

    assert not parser_test_wildcard.match(base_path / "hello")
    assert not parser_test_wildcard.match(base_path / "helloX")

    assert parser_test_wildcard.match(str(base_path) + "/hello.txt")
    assert parser_test_wildcard.match(str(base_path) + "/hello.foobar/")
    assert parser_test_wildcard.match(str(base_path) + "/dir/hello.txt")

    if platform.system() == "Windows":
        # in Windows there can be no files ending with a point
        assert not parser_test_wildcard.match(str(base_path) + "/hello.")
    else:
        assert parser_test_wildcard.match(str(base_path) + "/hello.")

    assert not parser_test_wildcard.match(str(base_path) + "/hello")
    assert not parser_test_wildcard.match(str(base_path) + "/helloX")


def test_anchored_wildcard(parser_test_anchored_wildcard: igittigitt.IgnoreParser, base_path: pathlib.Path) -> None:
    assert parser_test_anchored_wildcard.match(base_path / "hello.txt")
    assert parser_test_anchored_wildcard.match(base_path / "hello.c")
    assert not parser_test_anchored_wildcard.match(base_path / "a/hello.java")

    assert parser_test_anchored_wildcard.match(str(base_path) + "/hello.txt")
    assert parser_test_anchored_wildcard.match(str(base_path) + "/hello.c")
    assert not parser_test_anchored_wildcard.match(str(base_path) + "/a/hello.java")


def test_negation_rules(parser_negation_git_rules: igittigitt.IgnoreParser, base_path: pathlib.Path) -> None:
    assert parser_negation_git_rules.match(base_path / "trash.ignore")
    assert parser_negation_git_rules.match(base_path / "whatever.ignore")
    assert not parser_negation_git_rules.match(base_path / "keep.ignore")
    assert not parser_negation_git_rules.match(base_path.parent / "bitranox/keep.ignore")

    assert parser_negation_git_rules.match(str(base_path) + "/trash.ignore")
    assert parser_negation_git_rules.match(str(base_path) + "/whatever.ignore")
    assert not parser_negation_git_rules.match(str(base_path) + "/keep.ignore")
    assert not parser_negation_git_rules.match(str(base_path.parent) + "/bitranox/keep.ignore")


def test_match_does_not_resolve_symlinks(tmp_path: pathlib.Path) -> None:
    """Test match on files under symlinked directories
    This mimics how virtual environment sets up the .venv directory by
    symlinking to an interpreter. This test is to ensure that the symlink is
    being ignored (matched) correctly.

    """
    gitignore = igittigitt.IgnoreParser()
    gitignore.add_rule(".venv", tmp_path)
    linked_python = tmp_path / ".venv" / "bin" / "python"
    linked_python.parent.mkdir(parents=True)
    linked_python.symlink_to(pathlib.Path(sys.executable).resolve())
    assert gitignore.match(linked_python)


def test_match_files_under_symlink(tmp_path: pathlib.Path) -> None:
    """
    see: https://git-scm.com/docs/gitignore#_pattern_format
    The pattern foo/ will match a directory foo and paths underneath it,
    but will not match a regular file or a symbolic link foo
    (this is consistent with the way how pathspec works in general in Git)
    """
    pass


def test_handle_base_directories_with_a_symlink_in_their_components(tmp_path: pathlib.Path) -> None:
    """
    see https://github.com/bitranox/igittigitt/issues/28
    """
    # setup
    dir01 = pathlib.Path(tmp_path / "igittigitt01")
    dir01.mkdir(parents=True)
    dir02 = pathlib.Path(tmp_path / "symlink_to_igittigitt01")
    dir02.symlink_to(dir01)
    (dir02 / "file.txt").touch()

    # Test
    gitignore = igittigitt.IgnoreParser()
    gitignore.add_rule("*.txt", dir02)
    assert gitignore.match(dir02 / "file.txt")


def test_match_expands_user() -> None:
    """Test match expands `~` in path."""
    gitignore = igittigitt.IgnoreParser()
    gitignore.add_rule("test.txt", pathlib.Path("~").expanduser())
    assert gitignore.match(pathlib.Path("~") / "test.txt")
    assert gitignore.match("~/test.txt")


def test_parse_rule_files() -> None:
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
        ".test_gitignore_empty",
        "excluded_not",
        "excluded_not.txt",
        "not_excluded",
        "not_excluded.txt",
        "not_excluded2",
        "not_excluded2.txt",
    ]


def test_shutil_ignore_function() -> None:
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
        path_source_dir,
        path_target_dir,
        ignore=ignore_parser.shutil_ignore,
    )

    assert len(list(path_target_dir.glob("**/*"))) == 9

    # Teardown
    shutil.rmtree(path_target_dir, ignore_errors=True)


def doctest_examples() -> None:
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
    >>> discard = shutil.copytree(path_source_dir, path_target_dir, ignore=ignore_parser.shutil_ignore)

    # test_shutil_ignore_function_Example}}}
    # Teardown
    >>> shutil.rmtree(path_target_dir, ignore_errors=True)


    """
    pass


def doctest_subdir_match_examples() -> None:
    """
    >>> path_test_dir = pathlib.Path(__file__).parent.resolve()
    >>> path_base_dir = path_test_dir / 'example'

    >>> # test rule with trailing slash like "pattern/"
    >>> # should match the directory and everything below - but not a file !
    >>> parser = igittigitt.IgnoreParser()
    >>> parser.add_rule('test__pycache__/', base_path=path_base_dir)
    >>> # test match directory
    >>> assert parser.match(path_base_dir / 'test__pycache__')
    >>> # test match file under directory
    >>> assert parser.match(path_base_dir / 'test__pycache__/some_file.txt')
    >>> # test match directory under directory
    >>> assert parser.match(path_base_dir / 'test__pycache__/excluded')
    >>> assert parser.match(path_base_dir / 'test__pycache__/excluded/excluded')
    >>> assert parser.match(path_base_dir / 'test__pycache__/excluded/excluded/excluded.txt')

    >>> # this must not match the file "test__pycache__/test"
    >>> parser = igittigitt.IgnoreParser()
    >>> parser.add_rule('test__pycache__/test/', base_path=path_base_dir)
    >>> assert not parser.match(path_base_dir / 'test__pycache__/test')

    """
    pass


if __name__ == "__main__":
    pytest.main(["--log-cli-level", "ERROR"])
