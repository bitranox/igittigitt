# STDLIB
import glob
import os  # noqa
import pathlib
import platform
import sys
from types import TracebackType
from typing import Any, List, Optional, Set, Type, Union  # noqa

# EXT
import attr
import wcmatch.glob  # type: ignore

# CONF
try:
    from .conf_igittigitt import conf_igittigitt
except ImportError:  # pragma: no cover
    from conf_igittigitt import conf_igittigitt  # type: ignore  # pragma: no cover

PathLikeOrString = Union[str, "os.PathLike[Any]"]
__all__ = ("IgnoreParser",)


@attr.s(auto_attribs=True, eq=False, order=False, hash=False, slots=True)
class IgnoreRule(object):
    """
    the ignore rule datastructure
    we use attr here to get slotted class (less memory, faster access to attributes)
    and simplify the declaration of the class (we dont need __init__ method)
    """

    pattern_glob: str
    pattern_original: str
    is_negation_rule: bool
    match_file: bool  # if that rule should match also on Files - or only on Directories
    source_file: Optional[pathlib.Path]
    source_line_number: Optional[int]

    def __str__(self) -> str:
        """
        >>> # Setup
        >>> ignore_rule_1=IgnoreRule('./test_1/*', 'test_1', False, True, pathlib.Path('.gitignore'), 1)
        >>> ignore_rule_2=IgnoreRule('./test_1/*', 'test_1', True, True, pathlib.Path('.gitignore'), 2)
        >>> ignore_rule_3=IgnoreRule('./test_1/*', 'test_2', False, True, pathlib.Path('.gitignore'), 2)
        >>> ignore_rule_4=IgnoreRule('./test_1/*', 'test_3', True, True, pathlib.Path('.gitignore'), 3)
        >>> # Test str representation
        >>> assert str(ignore_rule_1) == './test_1/*'
        >>> assert str(ignore_rule_2) == '!./test_1/*'

        >>> # Test hash
        >>> assert ignore_rule_1.__hash__()

        >>> # Test equal
        >>> assert ignore_rule_1 == ignore_rule_3

        >>> # Test set
        >>> l_test = [ignore_rule_1, ignore_rule_2, ignore_rule_3, ignore_rule_4]
        >>> assert len(set(l_test)) == 2

        >>> # Test List in
        >>> l_test = [ignore_rule_1, ignore_rule_2]
        >>> assert ignore_rule_2 in l_test

        >>> # Test sorting
        >>> ignore_rule_sort_1=IgnoreRule('./test_sort_4/*', 'test_1', False, True, pathlib.Path('.gitignore'), 1)
        >>> ignore_rule_sort_2=IgnoreRule('./test_sort_3/*', 'test_1', False, True, pathlib.Path('.gitignore'), 2)
        >>> ignore_rule_sort_3=IgnoreRule('./test_sort_2/*', 'test_2', False, True, pathlib.Path('.gitignore'), 2)
        >>> ignore_rule_sort_4=IgnoreRule('./test_sort_1/*', 'test_3', False, True, pathlib.Path('.gitignore'), 3)
        >>> l_test_sort = [ignore_rule_sort_1, ignore_rule_sort_2, ignore_rule_sort_3, ignore_rule_sort_4]
        >>> assert str(sorted(l_test_sort)[0]) == './test_sort_1/*'

        >>> # Test __lt__, __gt__
        >>> assert ignore_rule_sort_1.__gt__(ignore_rule_sort_2)
        >>> assert ignore_rule_sort_2.__lt__(ignore_rule_sort_1)


        """
        l_str_pattern_glob: List[str] = list()
        if self.is_negation_rule:
            l_str_pattern_glob.append("!")
        l_str_pattern_glob.append(self.pattern_glob)
        if not self.match_file:
            l_str_pattern_glob.append("/")
        str_pattern_glob = "".join(l_str_pattern_glob)
        return str_pattern_glob

    def __eq__(self, other: object) -> bool:
        # return self.pattern_glob == other.pattern_glob and self.is_negation_rule == other.is_negation_rule
        return self.__str__() == other.__str__()

    def __lt__(self, other: object) -> bool:
        return self.__str__() < other.__str__()

    def __gt__(self, other: object) -> bool:
        return self.__str__() > other.__str__()

    def __hash__(self) -> int:
        int_hash = hash((self.pattern_glob, self.is_negation_rule))
        return int_hash


# IgnoreParser{{{
class IgnoreParser(object):
    def __init__(self) -> None:
        """
        init the igittigitt parser.
        """
        # IgnoreParser}}}

        self.rules: List[IgnoreRule] = list()
        self.negation_rules: List[IgnoreRule] = list()
        # small optimization - we have a
        # good chance that the last rule
        # might match again
        self.last_matching_rule: Optional[IgnoreRule] = None

    def __enter__(self) -> "IgnoreParser":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    @staticmethod
    def _expand_base_path(base_path: PathLikeOrString) -> pathlib.Path:
        """
        expand the user directory and make absolute, but dont resolve symlinks
        """
        path_base_dir = pathlib.Path(os.path.abspath(os.path.expanduser(base_path)))
        return path_base_dir

    # parse_rule_files{{{
    def parse_rule_files(
        self, base_dir: PathLikeOrString, filename: str = ".gitignore", add_default_patterns: bool = conf_igittigitt.add_default_patterns
    ) -> None:
        """
        get all the rule files (default = '.gitignore') from the base_dir
        all subdirectories will be searched for <filename> and the rules will be appended


        Parameter
        ---------
        path_base_dir
            the base directory - all subdirectories will be searched for <filename>
        filename
            the rule filename, default = '.gitignore'
        add_default_patterns
            if to add the default ignore patterns from user home directory. Those default patterns may reside at :

            LINUX : $XDG_CONFIG_HOME/git/ignore, if not set or empty
                    $HOME/.config/git/ignore

            WINDOWS : %XDG_CONFIG_HOME%/git/ignore, if not set or empty
                      %HOME%/.config/git/ignore,  if not set or empty
                      %USERDATA%/git/ignore

        Examples
        --------

        >>> # test empty rule file
        >>> path_test_dir = pathlib.Path(__file__).parent.parent.resolve() / 'tests'
        >>> path_source_dir = path_test_dir / 'example'

        >>> # parse existing file with rules
        >>> ignore_parser=IgnoreParser()
        >>> ignore_parser.parse_rule_files(path_test_dir, '.test_gitignore')

        >>> # parse existing file without rules
        >>> ignore_parser=IgnoreParser()
        >>> ignore_parser.parse_rule_files(path_test_dir, '.test_gitignore_empty')

        >>> # parse none existing file
        >>> ignore_parser=IgnoreParser()
        >>> ignore_parser.parse_rule_files(path_test_dir, '.test_not_existing')

        """
        # parse_rule_files}}}

        path_base_dir = self._expand_base_path(base_path=base_dir)

        if add_default_patterns:
            self._add_default_patterns(path_base_dir=path_base_dir)

        # we need to sort to get the right order.
        # we ignore git files in ignored directories !

        rule_files = sorted(list(glob.glob(f"{path_base_dir}/**/{filename.strip()}", recursive=True)))

        for rule_file in rule_files:
            if not self.match(rule_file):
                self.parse_rule_file(rule_file)

    def parse_rule_file(self, rule_file: PathLikeOrString, base_dir: Optional[PathLikeOrString] = None) -> None:
        """
        parse a git ignore file, create rules from a gitignore file

        Parameter
        ---------
        full_path
            the full path to the ignore file

        base_dir
            since gitignore patterns are relative to a base
            directory, that can be provided here.
            if it is not provided, path_base_dir is the location of the ignore file
            this is needed to be able to import default ignore files from user home directory,
            see README.RST, Section "Default Patterns"

        """
        path_rule_file = self._expand_base_path(base_path=rule_file)

        if not base_dir:
            path_base_dir = path_rule_file.parent
        else:
            path_base_dir = self._expand_base_path(base_path=base_dir)

        with open(path_rule_file) as ignore_file:
            counter = 0
            for line in ignore_file:
                counter += 1
                line = line.rstrip("\n")
                rules = get_rules_from_git_pattern(
                    git_pattern=line,
                    path_base_dir=path_base_dir,
                    path_source_file=path_rule_file,
                    source_line_number=counter,
                )
                if rules:
                    if rules[0].is_negation_rule:
                        self.negation_rules = self.negation_rules + rules
                    else:
                        self.rules = self.rules + rules
        self.rules = sorted(set(self.rules))
        self.negation_rules = sorted(set(self.negation_rules))

    # add_rule{{{
    def add_rule(self, pattern: str, base_path: PathLikeOrString) -> None:
        """
        add a rule as a string

        Parameter
        ---------
        pattern
            the pattern
        base_path
            since gitignore patterns are relative to a base
            directory, that needs to be provided here
        """
        # add_rule}}}
        path_base_dir = self._expand_base_path(base_path=base_path)
        rules = get_rules_from_git_pattern(git_pattern=pattern, path_base_dir=path_base_dir)

        if rules:
            if rules[0].is_negation_rule:
                self.negation_rules = sorted(set(self.negation_rules + rules))
            else:
                self.rules = sorted(set(self.rules + rules))

    # match{{{
    def match(self, file_path: PathLikeOrString) -> bool:
        """
        returns True if the path matches the rules

        >>> # Setup
        >>> base_path = pathlib.Path(__file__).parent.parent.resolve() / 'tests/example_negation'

        >>> # Test
        >>> gitignore = IgnoreParser()
        >>> gitignore.add_rule("/*", base_path)
        >>> gitignore.add_rule("!/foo", base_path)
        >>> gitignore.add_rule("/foo/*", base_path)
        >>> gitignore.add_rule("!/foo/bar", base_path)
        >>> assert gitignore.match(base_path / "foo/bar/file.txt") == False
        >>> # assert gitignore.match(base_path / "foo/other/file.txt") == True  # this fails - because everything is wrong
        >>> # see : https://docs.rs/ignore/0.4.18/ignore/struct.WalkBuilder.html

        """
        # match}}}
        path_file_object = self._expand_base_path(base_path=file_path)
        is_file = path_file_object.is_file()
        str_file_path = str(path_file_object)

        match = self._match_rules(str_file_path, is_file)

        if match:
            # we only need to look for negations if the path matches
            match = self._match_negation_rules(str_file_path)

        return match

    def _match_rules(self, str_file_path: str, is_file: bool) -> bool:
        """
        match without negations - in that case we can return
        immediately after a match.


        is_file:
            the passed path is a file (and not a directory)

        """

        # small optimisation - we have a good chance
        # that the last rule can match again
        if self.last_matching_rule:
            if is_file and not self.last_matching_rule.match_file:
                pass
            else:
                if wcmatch.glob.globmatch(
                    str_file_path,
                    [self.last_matching_rule.pattern_glob],
                    flags=wcmatch.glob.DOTGLOB | wcmatch.glob.GLOBSTAR,
                ):
                    return True

        for rule in self.rules:
            if is_file and not rule.match_file:
                pass
            else:
                if wcmatch.glob.globmatch(
                    str_file_path,
                    [rule.pattern_glob],
                    flags=wcmatch.glob.DOTGLOB | wcmatch.glob.GLOBSTAR,
                ):
                    self.last_matching_rule = rule
                    return True
        return False

    def _match_negation_rules(self, str_file_path: str) -> bool:
        """
        match with negation
        """
        for rule in self.negation_rules:
            if wcmatch.glob.globmatch(
                str_file_path,
                [rule.pattern_glob],
                flags=wcmatch.glob.DOTGLOB | wcmatch.glob.GLOBSTAR,
            ):
                self.last_matching_rule = rule
                return False
        return True

    def _add_default_patterns(self, path_base_dir: pathlib.Path, is_windows: Optional[bool] = None) -> None:
        """
        add the default ignore patterns from user home directory. Those default patterns may reside at :

        LINUX : $XDG_CONFIG_HOME/git/ignore, if not set or empty
                $HOME/.config/git/ignore

        WINDOWS : %XDG_CONFIG_HOME%/git/ignore, if not set or empty
                  %HOME%/.config/git/ignore,  if not set or empty
                  %USERDATA%/git/ignore

        >>> # setup
        >>> path_test_dir = pathlib.Path(__file__).parent.parent.resolve() / 'tests/default_pattern'
        >>> backup_env_xdg_config_home = get_env_data('XDG_CONFIG_HOME')
        >>> backup_env_home = get_env_data('HOME')
        >>> backup_env_userdata = get_env_data('USERDATA')
        >>> set_env_data('XDG_CONFIG_HOME', '')
        >>> set_env_data('HOME', '')
        >>> set_env_data('USERDATA', '')
        >>> ignore_parser=IgnoreParser()

        >>> # test XDG_CONFIG_HOME
        >>> ignore_parser.rules = list()
        >>> set_env_data('XDG_CONFIG_HOME', str(path_test_dir))
        >>> ignore_parser._add_default_patterns(path_base_dir=path_test_dir)
        >>> assert len(ignore_parser.rules) > 0
        >>> set_env_data('XDG_CONFIG_HOME', '')

        >>> # test HOME
        >>> ignore_parser.rules = list()
        >>> set_env_data('HOME', str(path_test_dir))
        >>> ignore_parser._add_default_patterns(path_base_dir=path_test_dir)
        >>> assert len(ignore_parser.rules) > 0
        >>> set_env_data('HOME', '')

        >>> # test USERDATA LINUX - this should NOT be found
        >>> ignore_parser.rules = list()
        >>> set_env_data('USERDATA', str(path_test_dir))
        >>> ignore_parser._add_default_patterns(path_base_dir=path_test_dir, is_windows=False)
        >>> assert len(ignore_parser.rules) == 0
        >>> set_env_data('USERDATA', '')

        >>> # test USERDATA WINDOWS
        >>> ignore_parser.rules = list()
        >>> set_env_data('USERDATA', str(path_test_dir))
        >>> ignore_parser._add_default_patterns(path_base_dir=path_test_dir, is_windows=True)
        >>> assert len(ignore_parser.rules) > 0
        >>> set_env_data('USERDATA', '')

        >>> # teardown
        >>> set_env_data('XDG_CONFIG_HOME', backup_env_xdg_config_home)
        >>> set_env_data('HOME', backup_env_home)
        >>> set_env_data('USERDATA', backup_env_userdata)

        """
        xdg_conf_home = get_env_data("XDG_CONFIG_HOME")
        usr_home = get_env_data("HOME")
        win_userdata = get_env_data("USERDATA")
        if is_windows is None:
            is_windows = platform.system() == "Windows"

        if xdg_conf_home:
            path_default_patterns = pathlib.Path(xdg_conf_home) / "git/ignore"

        elif usr_home:
            path_default_patterns = pathlib.Path(usr_home) / ".config/git/ignore"

        elif is_windows and win_userdata:
            path_default_patterns = pathlib.Path(win_userdata) / "git/ignore"

        else:
            return

        if path_default_patterns.is_file():
            self.parse_rule_file(rule_file=path_default_patterns, base_dir=path_base_dir)

    # shutil_ignore{{{
    def shutil_ignore(self, base_dir: str, file_names: List[str]) -> Set[str]:
        """
        Ignore function for shutil.copy_tree
        """
        # shutil_ignore}}}
        path_base_dir = self._expand_base_path(base_path=base_dir)
        ignore_files: Set[str] = set()
        for file in file_names:
            if self.match(path_base_dir / file):
                ignore_files.add(file)
        return ignore_files


def get_rules_from_git_pattern(
    git_pattern: str,
    path_base_dir: pathlib.Path,
    path_source_file: Optional[pathlib.Path] = None,
    source_line_number: Optional[int] = None,
) -> List[IgnoreRule]:
    """
    converts a git pattern to glob patterns

    >>> some_base_dir = pathlib.Path(__file__).parent.resolve()

    >>> # A blank line matches no files, so it can
    >>> # serve as a separator for readability.
    >>> assert get_rules_from_git_pattern('', some_base_dir) == []
    >>> assert get_rules_from_git_pattern(' ', some_base_dir) == []

    >>> # A line starting with # serves as a comment.
    >>> # Put a backslash ("\") in front of the first
    >>> # hash for patterns that begin with a hash.
    >>> assert get_rules_from_git_pattern('# some comment', some_base_dir) == []
    >>> assert get_rules_from_git_pattern('  # some comment', some_base_dir) == []
    >>> get_rules_from_git_pattern(r'  \\#some_file', some_base_dir)
    [IgnoreRule(pattern_glob='.../**/\\\\#some_file', ...)]

    >>> # Trailing spaces are ignored unless
    >>> # they are quoted with backslash ("\").
    >>> # in fact all spaces in gitignore CAN be escaped
    >>> # it is not clear if they NEED to be escaped,
    >>> # but it seems like !
    >>> # see: https://stackoverflow.com/questions/10213653
    >>> get_rules_from_git_pattern(r'something \\ ', some_base_dir)
    [IgnoreRule(pattern_glob='.../**/something\\\\ ', ...)]

    >>> # If there is a separator at the beginning or middle (or both)
    >>> # of the pattern, then the pattern is relative to the directory
    >>> # level of the particular .gitignore file itself.
    >>> # Otherwise the pattern may also match at any level
    >>> # below the .gitignore level.
    >>> assert get_match_anchored('/some/thing/')
    >>> assert not get_match_anchored('something/')

    >>> # test match at any level (no leading /)
    >>> get_rules_from_git_pattern(git_pattern='test', path_base_dir=pathlib.Path('/base_dir/'))
    [IgnoreRule(pattern_glob='/base_dir/**/test', ...), IgnoreRule(pattern_glob='/base_dir/**/test/**/*', ...)]

    >>> # test relative to gitignore file
    >>> get_rules_from_git_pattern(git_pattern='test/test2', path_base_dir=pathlib.Path('/base_dir/'))
    [IgnoreRule(pattern_glob='/base_dir/test/test2', ...), IgnoreRule(pattern_glob='/base_dir/test/test2/**/*', ...)]

    >>> # If there is a separator at the end of the pattern
    >>> # then the pattern will only match directories (and their contents)
    >>> # otherwise the pattern can match both files and directories

    >>> # Test Match Files, and Directories (and their content)
    >>> get_rules_from_git_pattern(git_pattern='test', path_base_dir=pathlib.Path('/base_dir/'))
    [IgnoreRule(pattern_glob='/base_dir/**/test', ...), IgnoreRule(pattern_glob='/base_dir/**/test/**/*', ...]


    >>> # Test Match Directories only (and their content)
    >>> get_rules_from_git_pattern(git_pattern='test/', path_base_dir=pathlib.Path('/base_dir/'))
    [IgnoreRule(pattern_glob='/base_dir/**/test', ..., match_file=False, ...), IgnoreRule(pattern_glob='/base_dir/**/test/**/*', ..., match_file=True, ...)]


    """
    match_dirs_and_content = True

    pattern_original = git_pattern
    git_pattern = git_pattern.lstrip()
    if not git_pattern or git_pattern.startswith("#"):
        return list()
    if git_pattern.startswith("!"):
        is_negation_rule = True
        git_pattern = git_pattern[1:]
    else:
        is_negation_rule = False

    git_pattern = git_pattern_handle_blanks(git_pattern)

    if get_match_files(git_pattern):
        match_file = True
    else:
        match_file = False

    git_pattern = git_pattern.rstrip("/")
    match_anchored = get_match_anchored(git_pattern)
    git_pattern = git_pattern.lstrip("/")

    if git_pattern.startswith("**/"):
        match_anchored = False
        git_pattern = git_pattern[3:]

    if git_pattern.endswith("/**"):
        match_file = False
        match_dirs_and_content = True
        git_pattern = git_pattern[:-3]

    l_ignore_rules = create_rule_variations(
        pattern=git_pattern,
        pattern_original=pattern_original,
        path_base_dir=path_base_dir,
        match_file=match_file,
        match_dirs_and_content=match_dirs_and_content,
        match_anchored=match_anchored,
        is_negation_rule=is_negation_rule,
        source_file=path_source_file,
        source_line_number=source_line_number,
    )

    return l_ignore_rules


def git_pattern_handle_blanks(git_pattern: str) -> str:
    """
    Trailing spaces are ignored unless
    they are quoted with backslash ("\").
    in fact all spaces in gitignore CAN be escaped
    it is not clear if they NEED to be escaped,
    but it seems like !
    see: https://stackoverflow.com/questions/10213653
    wcmatch.glob.globmatch supports both forms

    >>> assert git_pattern_handle_blanks(r'something \\ \\ ') == r'something\\ \\ '
    >>> assert git_pattern_handle_blanks(r'something \\ \\  ') == r'something\\ \\ '
    >>> assert git_pattern_handle_blanks(r'some\\ thing \\ ') == r'some\\ thing\\ '
    >>> assert git_pattern_handle_blanks(r'some thing \\ ') == r'some thing\\ '
    """
    parts = [part.strip() for part in git_pattern.split(r"\ ")]
    return r"\ ".join(parts)


def get_match_anchored(git_pattern: str) -> bool:
    """
    is the pattern relative to the ignore file base directory

    The slash / is used as the directory separator.
    Separators may occur at the beginning, middle or end of the
    .gitignore search pattern.
    If there is a separator at the beginning or middle (or both)
    of the pattern, then the pattern is relative to the directory
    level of the particular .gitignore file itself.
    Otherwise the pattern may also match at any level
    below the .gitignore level.

    >>> assert not get_match_anchored('')
    >>> assert not get_match_anchored('something')
    >>> assert get_match_anchored('some/thing')
    >>> assert get_match_anchored('/some/thing')
    >>> assert get_match_anchored('/some/thing/')
    >>> assert not get_match_anchored('something/')

    """
    return "/" in git_pattern.rstrip("/")


def get_match_files(git_pattern: str) -> bool:
    """
    If there is a separator at the end of the pattern
    then the pattern will match directories and their contents,
    otherwise the pattern can match both files and directories.

    >>> assert get_match_files('')
    >>> assert get_match_files('/something')
    >>> assert get_match_files('/some/thing')
    >>> assert not get_match_files('/some/thing/')
    """
    return not git_pattern.endswith("/")


def create_rule_variations(
    pattern: str,
    pattern_original: str,
    path_base_dir: pathlib.Path,
    match_file: bool,
    match_dirs_and_content: bool,
    match_anchored: bool,
    is_negation_rule: bool,
    source_file: Optional[pathlib.Path],
    source_line_number: Optional[int],
) -> List[IgnoreRule]:
    """
    create the variations of the rules, based on the parsed git line

    >>> path_base = pathlib.Path(__file__).parent.resolve()

    """
    str_path_base_dir = str(path_base_dir).replace("\\", "/")
    l_rules: List[IgnoreRule] = list()

    if match_anchored:
        pattern_resolved = str_path_base_dir + "/" + pattern
    else:
        pattern_resolved = str_path_base_dir + "/**/" + pattern

    # match the pattern, .../.../pattern
    # if match_file = True, it will also match on Files, otherwise only on directories
    rule_match_file = IgnoreRule(
        pattern_glob=pattern_resolved,
        pattern_original=pattern_original,
        is_negation_rule=is_negation_rule,
        match_file=match_file,
        source_file=source_file,
        source_line_number=source_line_number,
    )
    l_rules.append(rule_match_file)

    if match_dirs_and_content:
        rule_match_subdirs = IgnoreRule(
            pattern_glob=pattern_resolved + "/**/*",
            pattern_original=pattern_original,
            is_negation_rule=is_negation_rule,
            match_file=True,
            source_file=source_file,
            source_line_number=source_line_number,
        )
        l_rules.append(rule_match_subdirs)
    return l_rules


def get_env_data(env_variable: str) -> str:
    """
    >>> # Setup
    >>> save_mypy_path = get_env_data('MYPYPATH')

    >>> # Test
    >>> set_env_data('MYPYPATH', 'some_test')
    >>> assert get_env_data('MYPYPATH') == 'some_test'

    >>> # Teardown
    >>> set_env_data('MYPYPATH', save_mypy_path)

    """
    if env_variable in os.environ:
        env_data = os.environ[env_variable]
    else:
        env_data = ""
    return env_data


def set_env_data(env_variable: str, env_str: str) -> None:
    os.environ[env_variable] = env_str


if __name__ == "__main__":
    print(
        b'this is a library only, the executable is named "igittigitt_cli.py"',
        file=sys.stderr,
    )
