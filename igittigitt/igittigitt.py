# STDLIB
import os  # noqa
import pathlib
import sys
from types import TracebackType
from typing import Any, List, Optional, Set, Type, Union  # noqa

# EXT
import attr
import wcmatch.glob  # type: ignore

PathLikeOrString = Union[str, "os.PathLike[Any]"]
__all__ = ("IgnoreParser",)


@attr.s(auto_attribs=True)
class IgnoreRule(object):
    pattern_fnmatch: str
    pattern_original: str
    is_negation_rule: bool
    source_file: Optional[pathlib.Path]
    source_line_number: Optional[int]

    def __str__(self) -> str:
        return self.pattern_fnmatch


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

    def __call__(self,) -> None:
        self.__init__()  # type: ignore

    def __enter__(self) -> "IgnoreParser":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    # parse_rule_files{{{
    def parse_rule_files(
        self, base_dir: PathLikeOrString, filename: str = ".gitignore"
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
        """
        # parse_rule_files}}}

        path_base_dir = pathlib.Path(base_dir).resolve()
        # we need to sort to get the right order.
        # we ignore git files in ignored directories !
        rule_files = sorted(
            list(path_base_dir.glob("".join(["**/", filename.strip()])))
        )
        for rule_file in rule_files:
            if not self.match(rule_file):
                self._parse_rule_file(rule_file)

    def _parse_rule_file(
        self, rule_file: PathLikeOrString, base_dir: Optional[PathLikeOrString] = None,
    ) -> None:
        """
        parse a git ignore file, create rules from a gitignore file

        Parameter
        ---------
        full_path
            the full path to the ignore file
        base_dir
            optional base dir, for testing purposes only.
            the base dir is the parent of the rule file,
            because rules are relative to the directory
            were the rule file resides

        """
        if isinstance(rule_file, str):
            path_rule_file = pathlib.Path(rule_file).resolve()
        elif isinstance(rule_file, pathlib.Path):
            path_rule_file = rule_file.resolve()
        else:
            raise TypeError('wrong type for "rule_file"')

        if base_dir is None:
            path_base_dir = path_rule_file.parent
        elif isinstance(base_dir, str):
            path_base_dir = pathlib.Path(base_dir).resolve()
        elif isinstance(base_dir, pathlib.Path):
            path_base_dir = base_dir.resolve()
        else:
            raise TypeError('wrong type for "base_dir"')

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
        self.rules = sorted(self.rules)
        self.negation_rules = sorted(self.negation_rules)

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

        path_base_dir = pathlib.Path(base_path).resolve()

        rules = get_rules_from_git_pattern(
            git_pattern=pattern, path_base_dir=path_base_dir
        )

        if rules:
            if rules[0].is_negation_rule:
                self.negation_rules = sorted(self.negation_rules + rules)
            else:
                self.rules = sorted(self.rules + rules)

    # match{{{
    def match(self, file_path: PathLikeOrString) -> bool:
        """
        returns True if the path matches the rules
        """
        # match}}}

        str_file_path = str(pathlib.Path(file_path).resolve())

        match = self._match_rules(str_file_path)

        if match:
            # we only need to look for negations if the path matches
            match = self._match_negation_rules(str_file_path)

        return match

    def _match_rules(self, str_file_path: str) -> bool:
        """
        match without negotiations - in that case we can return
        immediately after a match.
        """

        # small optimisation - we have a good chance
        # that the last rule can match again
        if self.last_matching_rule:
            if wcmatch.glob.globmatch(
                str_file_path,
                [self.last_matching_rule.pattern_fnmatch],
                flags=wcmatch.glob.DOTGLOB | wcmatch.glob.GLOBSTAR,
            ):
                return True

        for rule in self.rules:
            if wcmatch.glob.globmatch(
                str_file_path,
                [rule.pattern_fnmatch],
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
                [rule.pattern_fnmatch],
                flags=wcmatch.glob.DOTGLOB | wcmatch.glob.GLOBSTAR,
            ):
                self.last_matching_rule = rule
                return False
        return True

    # shutil_ignore{{{
    def shutil_ignore(self, base_dir: str, file_names: List[str]) -> Set[str]:
        """
        Ignore function for shutil.copy_tree
        """
        # shutil_ignore}}}

        path_base_dir = pathlib.Path(base_dir).resolve()
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
    converts a git pattern to fnmatch pattern

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
    [IgnoreRule(pattern_fnmatch='.../**/\\\\#some_file', ...)]

    >>> # Trailing spaces are ignored unless
    >>> # they are quoted with backslash ("\").
    >>> # in fact all spaces in gitignore CAN be escaped
    >>> # it is not clear if they NEED to be escaped,
    >>> # but it seems like !
    >>> # see: https://stackoverflow.com/questions/10213653
    >>> get_rules_from_git_pattern(r'something \\ ', some_base_dir)
    [IgnoreRule(pattern_fnmatch='.../**/something\\\\ ', ...)]

    >>> # If there is a separator at the beginning or middle (or both)
    >>> # of the pattern, then the pattern is relative to the directory
    >>> # level of the particular .gitignore file itself.
    >>> # Otherwise the pattern may also match at any level
    >>> # below the .gitignore level.
    >>> assert not match_also_sub_directories('/some/thing/')
    >>> assert match_also_sub_directories('something/')

    >>> # If there is a separator at the end of the pattern
    >>> # then the pattern will only match directories,
    >>> # otherwise the pattern can match both files and directories.

    >>> assert not match_directory('/some/thing')
    >>> assert match_directory('/some/thing/')

    """
    match_files = True

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

    match_dirs = match_directory(git_pattern)
    git_pattern = git_pattern.rstrip("/")
    match_also_subdirs = match_also_sub_directories(git_pattern)
    git_pattern = git_pattern.lstrip("/")

    if git_pattern.startswith("**/"):
        match_also_subdirs = True
        git_pattern = git_pattern[3:]

    if git_pattern.endswith("/**"):
        match_files = False
        match_dirs = True
        git_pattern = git_pattern[:-3]

    l_patterns = create_pattern_variations(
        pattern=git_pattern,
        path_base_dir=path_base_dir,
        match_files=match_files,
        match_dirs=match_dirs,
        match_also_subdirs=match_also_subdirs,
    )
    l_ignore_rules: List[IgnoreRule] = list()
    for pattern in l_patterns:
        l_ignore_rules.append(
            IgnoreRule(
                pattern_fnmatch=pattern,
                pattern_original=pattern_original,
                is_negation_rule=is_negation_rule,
                source_file=path_source_file,
                source_line_number=source_line_number,
            )
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

    >>> assert git_pattern_handle_blanks(r'something \\ \\ ') == 'something\\ \\ '
    >>> assert git_pattern_handle_blanks(r'something \\ \\  ') == 'something\\ \\ '
    >>> assert git_pattern_handle_blanks(r'some\\ thing \\ ') == 'some\\ thing\\ '
    >>> assert git_pattern_handle_blanks(r'some thing \\ ') == 'some thing\\ '
    """
    parts = [part.strip() for part in git_pattern.split("\\ ")]
    return "\\ ".join(parts)


def match_also_sub_directories(git_pattern: str) -> bool:
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

    >>> assert match_also_sub_directories('')
    >>> assert match_also_sub_directories('something')
    >>> assert not match_also_sub_directories('some/thing')
    >>> assert not match_also_sub_directories('/some/thing')
    >>> assert not match_also_sub_directories('/some/thing/')
    >>> assert match_also_sub_directories('something/')

    """
    return "/" not in git_pattern.rstrip("/")


def match_directory(git_pattern: str) -> bool:
    """
    If there is a separator at the end of the pattern
    then the pattern will match directories and their contents,
    otherwise the pattern can match both files and directories.

    >>> assert not match_directory('')
    >>> assert not match_directory('/something')
    >>> assert not match_directory('/some/thing')
    >>> assert match_directory('/some/thing/')
    """
    return git_pattern.endswith("/")


def create_pattern_variations(
    pattern: str,
    path_base_dir: pathlib.Path,
    match_files: bool,
    match_dirs: bool,
    match_also_subdirs: bool,
) -> List[str]:
    """
    create the variations of the fnmatch patterns based on the parsed git line

    >>> path_base = pathlib.Path(__file__).parent.resolve()
    >>> create_pattern_variations(pattern='test', path_base_dir=path_base, match_files=True, match_dirs=True, match_also_subdirs=True)
    ['.../**/test', '.../**/test/**/*']
    >>> create_pattern_variations(pattern='test', path_base_dir=path_base, match_files=True, match_dirs=True, match_also_subdirs=False)
    ['.../test', '.../test/**/*']

    """
    str_path_base_dir = str(path_base_dir).replace("\\", "/")
    l_patterns: List[str] = list()

    if match_also_subdirs:
        pattern_match_file_in_subdirs = str_path_base_dir + "/**/" + pattern
        if match_files:
            l_patterns.append(pattern_match_file_in_subdirs)
        if match_dirs:
            l_patterns.append(pattern_match_file_in_subdirs + "/**/*")
    else:
        pattern_match_file = str_path_base_dir + "/" + pattern
        if match_files:
            l_patterns.append(pattern_match_file)
        if match_dirs:
            l_patterns.append(pattern_match_file + "/**/*")

    return l_patterns


if __name__ == "__main__":
    print(
        b'this is a library only, the executable is named "igittigitt_cli.py"',
        file=sys.stderr,
    )
