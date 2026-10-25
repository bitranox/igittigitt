# STDLIB
import functools
import os
import pathlib
import platform
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Union

# EXT
import wcmatch.glob  # type: ignore
from pydantic import BaseModel, ConfigDict, field_validator

# CONF
from .conf_igittigitt import conf_igittigitt

PathLikeOrString = Union[str, "os.PathLike[Any]"]
__all__ = ("IgnoreParser", "IncludeParser")

#: Upper bound for the per-instance directory-decision LRU cache. Keeps memory
#: O(this), not O(#directories), while capturing the locality of a top-down tree
#: walk (copytree / sorted find output), where the active ancestor chain repeats.
_DIR_CACHE_MAX = 8192

#: Sentinel for "key absent" - the cache legitimately stores ``None`` (not pruned).
_CACHE_MISS: Any = object()

_WCMATCH_FLAGS = wcmatch.glob.DOTGLOB | wcmatch.glob.GLOBSTAR


class _UserIgnoreDirs(BaseModel):
    """The environment variables that locate git's user-level ignore file, read once.

    An empty variable counts as unset, as git treats an empty ``XDG_CONFIG_HOME``. ``HOMEDRIVE``
    and ``HOMEPATH`` stay text: git joins them as plain strings before they name a directory.

    >>> _UserIgnoreDirs(xdg_config_home="", home="/home/u").git_home(is_windows=False).as_posix()
    '/home/u'
    """

    model_config = ConfigDict(frozen=True)

    xdg_config_home: pathlib.Path | None = None
    home: pathlib.Path | None = None
    homedrive: str | None = None
    homepath: str | None = None
    userprofile: pathlib.Path | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _empty_is_unset(cls, value: str | None) -> str | None:
        return value or None

    @classmethod
    def from_environ(cls) -> "_UserIgnoreDirs":
        return cls.model_validate(
            {
                "xdg_config_home": os.environ.get("XDG_CONFIG_HOME"),
                "home": os.environ.get("HOME"),
                "homedrive": os.environ.get("HOMEDRIVE"),
                "homepath": os.environ.get("HOMEPATH"),
                "userprofile": os.environ.get("USERPROFILE"),
            }
        )

    def git_home(self, *, is_windows: bool) -> pathlib.Path | None:
        """The directory git treats as home, or None when it has none.

        ``HOME`` everywhere. On Windows, when ``HOME`` is unset, git for Windows sets it at
        startup (``compat/mingw.c``): to ``HOMEDRIVE`` + ``HOMEPATH`` (plain concatenation) if
        that is an existing directory, otherwise to ``USERPROFILE``. Measured against git
        2.56.0.windows.3; tests/test_default_patterns.py pins each branch.

        >>> _UserIgnoreDirs(userprofile="C:/Users/me").git_home(is_windows=True).as_posix()
        'C:/Users/me'
        >>> _UserIgnoreDirs(userprofile="C:/Users/me").git_home(is_windows=False) is None
        True
        """
        if self.home is not None:
            return self.home
        if not is_windows:
            return None
        if self.homedrive is not None and self.homepath is not None:
            drive_home = pathlib.Path(self.homedrive + self.homepath)
            if _is_directory(drive_home):
                return drive_home
        return self.userprofile


def _is_directory(path: pathlib.Path) -> bool:
    """Whether *path* is a directory; one that cannot be examined is not, as for git's stat check.

    ``Path.is_dir`` re-raises a permission error before Python 3.14, so it is caught here.
    """
    try:
        return path.is_dir()
    except OSError:
        return False


def _find_rule_files(path_base_dir: pathlib.Path, filename: str) -> list[pathlib.Path]:
    """
    Every *filename* below *path_base_dir*, hidden directories included.

    Like git, this does not look inside ``.git`` and does not follow symlinks
    to directories. ``glob`` does not fit: its ``**`` skips hidden directories
    such as ``.config``, and it reads glob characters in *path_base_dir* as a
    pattern.
    """
    rule_files: list[pathlib.Path] = []
    for dirpath, dirnames, filenames in os.walk(path_base_dir):
        dirnames[:] = [dirname for dirname in dirnames if dirname != ".git"]
        if filename in filenames:
            rule_files.append(pathlib.Path(dirpath) / filename)
    return rule_files


@functools.lru_cache(maxsize=4096)
def _compiled_pattern(pattern_glob: str) -> "re.Pattern[str]":
    """
    Translate one glob to a compiled, anchored regex (cached).

    ``wcmatch`` produces the regex via its own faithful translation, so behaviour
    is identical to ``wcmatch.glob.globmatch`` - but matching with a precompiled
    ``re.Pattern`` is roughly 8x faster per call than ``globmatch`` (which carries
    per-call setup overhead). The cache is bounded by ``maxsize`` (so memory
    scales with the number of distinct patterns, never with the number of paths).
    """
    regex = wcmatch.glob.translate([pattern_glob], flags=_WCMATCH_FLAGS)[0][0]
    return re.compile(regex)


def _globmatch(str_file_path: str, pattern_glob: str) -> bool:
    """Match a single (already resolved, forward-slash) path against one glob pattern."""
    return _compiled_pattern(pattern_glob).match(str_file_path) is not None


def set_pattern_cache_size(maxsize: int) -> None:
    """Resize the process-wide compiled-pattern cache (see ``pattern_cache_max``).

    ``maxsize`` of ``0`` disables caching (every match recompiles); ``None`` makes
    it unbounded (bounded in practice by the number of distinct patterns).
    """
    global _compiled_pattern  # noqa: PLW0603 - intentional: resize the process-wide cache
    _compiled_pattern = functools.lru_cache(maxsize=maxsize)(_compiled_pattern.__wrapped__)


@dataclass(slots=True, eq=False)
class IgnoreRule:
    """
    the ignore rule datastructure.

    A slotted dataclass (less memory, faster attribute access) with custom
    ordering/equality so rules compare by their string representation.
    """

    pattern_glob: str
    pattern_original: str
    is_negation_rule: bool
    match_file: bool  # if that rule should match also on Files - or only on Directories
    source_file: pathlib.Path | None
    source_line_number: int | None

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
        l_str_pattern_glob: list[str] = list()
        if self.is_negation_rule:
            l_str_pattern_glob.append("!")
        l_str_pattern_glob.append(self.pattern_glob)
        if not self.match_file:
            l_str_pattern_glob.append("/")
        str_pattern_glob = "".join(l_str_pattern_glob)
        return str_pattern_glob

    def __eq__(self, other: object) -> bool:
        return self.__str__() == other.__str__()

    def __lt__(self, other: object) -> bool:
        return self.__str__() < other.__str__()

    def __gt__(self, other: object) -> bool:
        return self.__str__() > other.__str__()

    def __hash__(self) -> int:
        int_hash = hash((self.pattern_glob, self.is_negation_rule))
        return int_hash


class _BaseParser:
    """
    Shared rule storage and parsing for the ignore and include parsers.

    Rules are kept in a **single ordered list** in the exact order they were
    read (per-directory by depth, then by line number). This preserves git's
    semantics where the *last* matching pattern decides the outcome - unlike the
    historical implementation which sorted and de-duplicated the rules and so
    could not reproduce git behaviour for negations and nested precedence.

    Memory note: the parser only ever holds the compiled rules (bounded by the
    number of patterns across the rule files), never a collection that grows
    with the number of matched paths.
    """

    def __init__(self, dir_cache_max: int = _DIR_CACHE_MAX) -> None:
        #: cap of the directory-decision LRU (0 disables it); see config knob
        #: ``performance.dir_cache_max``.
        self._dir_cache_max = dir_cache_max
        self.rules: list[IgnoreRule] = list()
        # bounded LRU of directory -> pruning rule (or None). Lets the ancestor
        # walk reuse decisions for sibling paths that share a parent directory.
        self._dir_cache: OrderedDict[str, IgnoreRule | None] = OrderedDict()

    def _invalidate_caches(self) -> None:
        """Drop cached decisions after the rule set changes."""
        self._dir_cache.clear()

    def __enter__(self) -> "_BaseParser":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    @staticmethod
    def _expand_base_path(base_path: PathLikeOrString) -> pathlib.Path:
        """
        expand the user directory and make absolute, but dont resolve symlinks
        """
        base_path_str = os.fspath(base_path)
        path_base_dir = pathlib.Path(os.path.abspath(os.path.expanduser(base_path_str)))
        return path_base_dir

    def parse_rule_files(
        self,
        base_dir: PathLikeOrString,
        filename: str = ".gitignore",
        add_default_patterns: bool | None = None,
    ) -> None:
        """
        get all the rule files (default = '.gitignore') from the base_dir
        all subdirectories will be searched for <filename> and the rules will be appended.

        The rule files are processed shallow-first (by directory depth) so that
        rules from deeper ``.gitignore`` files are appended *after* shallower
        ones and therefore win under last-match-wins - exactly git's per-directory
        precedence. ``.gitignore`` files inside already-ignored directories are
        skipped, mirroring git (it never descends into excluded directories).

        Parameter
        ---------
        base_dir
            the base directory - all subdirectories will be searched for <filename>
        filename
            the rule filename, default = '.gitignore'
        add_default_patterns
            whether to also add git's user-level ignore file (see :meth:`_add_default_patterns`);
            None reads ``conf_igittigitt.add_default_patterns`` when the call runs.

        Examples
        --------

        >>> # test empty rule file
        >>> path_test_dir = pathlib.Path(__file__).resolve().parents[2] / 'tests'

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
        path_base_dir = self._expand_base_path(base_path=base_dir)

        if add_default_patterns is None:
            add_default_patterns = conf_igittigitt.add_default_patterns
        if add_default_patterns:
            self._add_default_patterns(path_base_dir=path_base_dir)

        rule_files = _find_rule_files(path_base_dir, filename.strip())
        # shallow first so deeper .gitignore rules are appended last (win),
        # tie-break by path for deterministic ordering.
        rule_files.sort(key=lambda p: (len(p.parts), str(p)))

        for rule_file in rule_files:
            if not self._path_is_ignored_for_discovery(rule_file):
                self.parse_rule_file(rule_file)

    def _path_is_ignored_for_discovery(self, rule_file: pathlib.Path) -> bool:
        """Whether a discovered rule file lives in an already-ignored directory."""
        # default: never skip (overridden by IgnoreParser to honour ignore state)
        return False

    def parse_rule_file(self, rule_file: PathLikeOrString, base_dir: PathLikeOrString | None = None) -> None:
        """
        parse a git ignore file, create rules from a gitignore file.

        Rules are appended in file order (no sorting, no de-duplication) so that
        last-match-wins reproduces git semantics.

        Parameter
        ---------
        rule_file
            the full path to the ignore file
        base_dir
            since gitignore patterns are relative to a base directory, that can
            be provided here. If not provided, the location of the ignore file
            is used (needed to import default ignore files from the user home
            directory, see :meth:`_add_default_patterns`).
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
                self.rules.extend(rules)
        self._invalidate_caches()

    def load_default_patterns(self, base_dir: PathLikeOrString) -> None:
        """Load git's default ignore patterns from the user home directory.

        Convenience wrapper so callers do not need to reach for the internal
        ``_add_default_patterns`` helper. See :meth:`parse_rule_files` for where
        those default patterns live.
        """
        self._add_default_patterns(path_base_dir=self._expand_base_path(base_path=base_dir))

    def add_rule(self, pattern: str, base_path: PathLikeOrString) -> None:
        """
        add a rule as a string. The rule is appended in order (last-match-wins).

        Parameter
        ---------
        pattern
            the pattern
        base_path
            since gitignore patterns are relative to a base directory, that
            needs to be provided here
        """
        path_base_dir = self._expand_base_path(base_path=base_path)
        rules = get_rules_from_git_pattern(git_pattern=pattern, path_base_dir=path_base_dir)
        self.rules.extend(rules)
        self._invalidate_caches()

    def _last_matching_rule(self, str_file_path: str, is_file: bool) -> IgnoreRule | None:
        """
        Return the *last* rule (in insertion order) that matches the path, or
        ``None``. We iterate in reverse and return the first hit, which is the
        last match - so this is O(#rules) worst case but usually short-circuits.

        is_file:
            the passed path is a file (and not a directory); rules that only
            match directories (``match_file == False``) are skipped for files.
        """
        for rule in reversed(self.rules):
            if is_file and not rule.match_file:
                continue
            if _globmatch(str_file_path, rule.pattern_glob):
                return rule
        return None

    def _add_default_patterns(self, path_base_dir: pathlib.Path, is_windows: bool | None = None) -> None:
        """
        Add the rules of git's user-level ignore file, the one git reads when ``core.excludesFile``
        is not set:

        * ``$XDG_CONFIG_HOME/git/ignore`` when ``XDG_CONFIG_HOME`` is set and not empty;
        * otherwise ``.config/git/ignore`` in git's home directory (:meth:`_UserIgnoreDirs.git_home`:
          ``HOME``, and on Windows without ``HOME`` the ``HOMEDRIVE`` + ``HOMEPATH`` directory
          or ``USERPROFILE``).

        The variables are read through :class:`_UserIgnoreDirs`; tests/test_default_patterns.py
        covers each branch with the environment set per test.
        """
        user_dirs = _UserIgnoreDirs.from_environ()
        if is_windows is None:
            is_windows = platform.system() == "Windows"

        git_home = user_dirs.git_home(is_windows=is_windows)
        if user_dirs.xdg_config_home is not None:
            path_default_patterns = user_dirs.xdg_config_home / "git/ignore"
        elif git_home is not None:
            path_default_patterns = git_home / ".config/git/ignore"
        else:
            return

        if path_default_patterns.is_file():
            self.parse_rule_file(rule_file=path_default_patterns, base_dir=path_base_dir)


# IgnoreParser{{{
class IgnoreParser(_BaseParser):
    """
    A spec-compliant ``.gitignore`` parser.

    Add rules from ``.gitignore`` files (``parse_rule_files`` /
    ``parse_rule_file``) or as strings (``add_rule``), then query a path with
    ``match`` or use ``shutil_ignore`` directly as the ``ignore=`` callback of
    ``shutil.copytree``.

    Matching follows git exactly: a single ordered pass, last matching pattern
    wins, and a file cannot be re-included by a negation if one of its parent
    directories is excluded (git never descends into an excluded directory).
    """

    # IgnoreParser}}}

    def __enter__(self) -> "IgnoreParser":
        return self

    def _path_is_ignored_for_discovery(self, rule_file: pathlib.Path) -> bool:
        return self.match(rule_file)

    # match{{{
    def match(self, file_path: PathLikeOrString) -> bool:
        """
        returns True if the path is ignored by the rules - exactly as git would
        decide it, including correct handling of negations and the rule that a
        file cannot be re-included if a parent directory is excluded.

        >>> # Setup
        >>> base_path = pathlib.Path(__file__).resolve().parents[2] / 'tests/example_negation'

        >>> # Test: re-include of foo/bar wins, foo/bar/file.txt is NOT ignored
        >>> gitignore = IgnoreParser()
        >>> gitignore.add_rule("/*", base_path)
        >>> gitignore.add_rule("!/foo", base_path)
        >>> gitignore.add_rule("/foo/*", base_path)
        >>> gitignore.add_rule("!/foo/bar", base_path)
        >>> gitignore.match(base_path / "foo/bar/file.txt")
        False
        >>> # everything else under foo IS ignored (foo/* excludes it)
        >>> gitignore.match(base_path / "foo/other/file.txt")
        True

        """
        # match}}}
        ignored, _rule = self.match_with_rule(file_path)
        return ignored

    def match_with_rule(self, file_path: PathLikeOrString) -> "tuple[bool, IgnoreRule | None]":
        """
        Like :meth:`match`, but also return the rule that decided the outcome
        (or ``None`` if no rule matched). Useful for ``git check-ignore -v``
        style reporting.
        """
        path_file_object = self._expand_base_path(base_path=file_path)
        is_file = path_file_object.is_file()
        return self._ignore_decision(path_file_object, is_file)

    def _ignore_decision(self, path_file_object: pathlib.Path, is_file: bool) -> "tuple[bool, IgnoreRule | None]":
        """
        If any *ancestor directory* is excluded (and not re-included at its own
        level) the path is ignored and nothing below can re-include it. Otherwise
        the path's own last matching rule decides. The ancestor decision is
        memoized per directory (bounded LRU), so sibling paths sharing a parent
        do not recompute it. O(depth x #rules) on a cache miss, O(1) on a hit.
        """
        pruning_rule = self._ancestor_pruning_rule(path_file_object.parent)
        if pruning_rule is not None:
            return True, pruning_rule

        # the path itself
        rule = self._last_matching_rule(path_file_object.as_posix(), is_file=is_file)
        if rule is None:
            return False, None
        return (not rule.is_negation_rule), rule

    def _ancestor_pruning_rule(self, directory: pathlib.Path) -> IgnoreRule | None:
        """
        Return the rule that excludes *directory* or one of its ancestors (so its
        whole subtree is pruned), or ``None`` if none does. Memoized per directory
        in a bounded LRU; recurses into the parent so the shallowest excluding
        rule wins, matching git's top-down evaluation.
        """
        key = directory.as_posix()
        cache = self._dir_cache
        cached = cache.get(key, _CACHE_MISS)
        if cached is not _CACHE_MISS:
            cache.move_to_end(key)
            return cached  # type: ignore[return-value]

        parent = directory.parent
        result: IgnoreRule | None = None
        if parent != directory:
            result = self._ancestor_pruning_rule(parent)
        if result is None:
            rule = self._last_matching_rule(key, is_file=False)
            if rule is not None and not rule.is_negation_rule:
                result = rule

        if self._dir_cache_max > 0:
            cache[key] = result
            cache.move_to_end(key)
            if len(cache) > self._dir_cache_max:
                cache.popitem(last=False)
        return result

    # shutil_ignore{{{
    def shutil_ignore(self, base_dir: str, file_names: list[str]) -> set[str]:
        """
        Ignore callback for ``shutil.copytree`` - returns the names to ignore.

        Streams per directory (copytree calls this once per directory), so it
        never builds a structure that grows with the total number of files.
        """
        # shutil_ignore}}}
        # copytree passes bare names from os.listdir (never '..' or a leading '~'), so joining
        # them onto the expanded base is already the absolute path; going through the public
        # match() would re-normalise every entry, a large share of the per-entry cost when the
        # .gitignore has few rules.
        path_base_dir = self._expand_base_path(base_path=base_dir)
        ignore_files: set[str] = set()
        for file in file_names:
            full = path_base_dir / file
            ignored, _rule = self._ignore_decision(full, is_file=full.is_file())
            if ignored:
                ignore_files.add(file)
        return ignore_files


class IncludeParser(_BaseParser):
    """
    The inverse of :class:`IgnoreParser`: patterns describe what to **keep**
    (an allow-list / whitelist), everything else is dropped.

    The mode is directory-aware (rsync-like): a directory is kept if any
    descendant could match a keep pattern, so it works correctly as a
    ``shutil.copytree`` filter for deeply nested includes. Whether to descend
    into a directory is decided by static analysis of the patterns
    (O(#patterns)), never by enumerating the directory's descendants - so
    memory stays bounded even for trees with millions of entries.

    A negated pattern (``!pattern``) drops matches that an earlier include
    pattern would otherwise keep.
    """

    def __init__(self, dir_cache_max: int = _DIR_CACHE_MAX) -> None:
        super().__init__(dir_cache_max=dir_cache_max)
        # memo of directory -> highest (insertion-index, rule) matching that
        # directory or any of its ancestors; bounded LRU, like the ignore cache.
        self._keep_cache: OrderedDict[str, tuple[int, IgnoreRule] | None] = OrderedDict()
        # cached descend-prefix globs (recomputed only when the rules change).
        self._descend_cache: list[str] | None = None

    def __enter__(self) -> "IncludeParser":
        return self

    def _invalidate_caches(self) -> None:
        super()._invalidate_caches()
        self._keep_cache.clear()
        self._descend_cache = None

    def _highest_match(self, str_path: str, is_file: bool) -> tuple[int, IgnoreRule] | None:
        """Highest-insertion-index rule matching *str_path*, or ``None``."""
        total = len(self.rules)
        for offset, rule in enumerate(reversed(self.rules)):
            if is_file and not rule.match_file:
                continue
            if _globmatch(str_path, rule.pattern_glob):
                return total - 1 - offset, rule
        return None

    def _ancestor_keep(self, directory: pathlib.Path) -> tuple[int, IgnoreRule] | None:
        """
        Highest (index, rule) matching *directory* or any ancestor (as dirs).
        Memoized per directory in a bounded LRU so siblings reuse it.
        """
        key = directory.as_posix()
        cache = self._keep_cache
        cached = cache.get(key, _CACHE_MISS)
        if cached is not _CACHE_MISS:
            cache.move_to_end(key)
            return cached  # type: ignore[return-value]

        parent = directory.parent
        best = self._ancestor_keep(parent) if parent != directory else None
        here = self._highest_match(key, is_file=False)
        if here is not None and (best is None or here[0] > best[0]):
            best = here

        if self._dir_cache_max > 0:
            cache[key] = best
            cache.move_to_end(key)
            if len(cache) > self._dir_cache_max:
                cache.popitem(last=False)
        return best

    def _keep_decision(self, path_file_object: pathlib.Path, is_dir: bool) -> bool:
        """
        True if the path is whitelisted. A directory include cascades to its
        contents: the path is kept if the *last* (insertion order) rule matching
        the path itself or any ancestor directory is a (non-negation) include.
        A later negation re-excludes within an included tree (rsync-like).
        """
        best = self._highest_match(path_file_object.as_posix(), is_file=not is_dir)
        ancestor = self._ancestor_keep(path_file_object.parent)
        if ancestor is not None and (best is None or ancestor[0] > best[0]):
            best = ancestor
        return best is not None and not best[1].is_negation_rule

    def _descend_globs(self) -> list[str]:
        """
        Directory globs that must be descended into to reach any keep match.

        For each include (non-negation) rule we generate the cumulative path
        prefixes of its glob - e.g. ``/base/**/test`` yields ``/base``,
        ``/base/**`` and ``/base/**/test``. A directory is descended into if it
        matches one of these prefixes. Bounded by #rules x path depth; computed
        once and cached until the rules change.
        """
        if self._descend_cache is not None:
            return self._descend_cache
        seen: set[str] = set()
        globs: list[str] = list()
        for rule in self.rules:
            if rule.is_negation_rule:
                continue
            parts = rule.pattern_glob.split("/")
            prefix = ""
            for index, part in enumerate(parts):
                prefix = part if index == 0 else f"{prefix}/{part}"
                if prefix and prefix not in seen:
                    seen.add(prefix)
                    globs.append(prefix)
        self._descend_cache = globs
        return globs

    def match(self, file_path: PathLikeOrString) -> bool:
        """
        returns True if the path is kept by the include rules.

        A file is kept if it matches an include pattern (and is not negated).
        A directory is kept if it is itself whitelisted *or* if any descendant
        could match - so that copytree descends into it.

        >>> base = pathlib.Path(__file__).resolve().parents[2] / 'tests/example'
        >>> inc = IncludeParser()
        >>> inc.add_rule("*.txt", base)
        >>> # a deep .txt file is kept ...
        >>> inc.match(base / "test__pycache__/some_file.txt")
        True
        >>> # ... and its parent directory is kept so copytree descends into it
        >>> inc.match(base / "test__pycache__")
        True
        >>> # a non-matching leaf is dropped
        >>> inc.match(base / "test__pycache__/test")
        False
        """
        path_file_object = self._expand_base_path(base_path=file_path)
        # Treat non-existent paths as leaves (a stdin filter passes paths that
        # may not exist on disk); only descend into genuine directories.
        is_dir = path_file_object.is_dir()
        if self._keep_decision(path_file_object, is_dir=is_dir):
            return True
        if is_dir:
            posix = path_file_object.as_posix()
            for descend_glob in self._descend_globs():
                if _globmatch(posix, descend_glob):
                    return True
        return False

    def shutil_include(self, base_dir: str, file_names: list[str]) -> set[str]:
        """
        Ignore callback for ``shutil.copytree`` for include mode - returns the
        names to ignore, i.e. everything that is **not** kept. Pass it directly
        as ``shutil.copytree(src, dst, ignore=parser.shutil_include)``.

        Streams per directory; no structure that grows with the file count.
        """
        path_base_dir = self._expand_base_path(base_path=base_dir)
        descend_globs = self._descend_globs()
        ignore_files: set[str] = set()
        for file in file_names:
            full = path_base_dir / file
            is_dir = full.is_dir()
            if self._keep_decision(full, is_dir=is_dir):
                continue
            if is_dir and any(_globmatch(full.as_posix(), descend_glob) for descend_glob in descend_globs):
                continue
            ignore_files.add(file)
        return ignore_files


def get_rules_from_git_pattern(
    git_pattern: str,
    path_base_dir: pathlib.Path,
    path_source_file: pathlib.Path | None = None,
    source_line_number: int | None = None,
) -> list[IgnoreRule]:
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
    >>> get_rules_from_git_pattern(r'something \\ ', some_base_dir)
    [IgnoreRule(pattern_glob='.../**/something\\\\ ', ...)]

    >>> # If there is a separator at the beginning or middle (or both)
    >>> # of the pattern, then the pattern is relative to the directory
    >>> # level of the particular .gitignore file itself.
    >>> # Otherwise the pattern may also match at any level
    >>> # below the .gitignore level.
    >>> assert get_match_anchored('/some/thing/')
    >>> assert not get_match_anchored('something/')

    >>> # A single rule matches the path at its own level; directory exclusion
    >>> # cascades to the contents via ancestor pruning at match time (git model),
    >>> # so no separate "contents" rule is emitted for ordinary patterns.

    >>> # test match at any level (no leading /)
    >>> get_rules_from_git_pattern(git_pattern='test', path_base_dir=pathlib.Path('/base_dir/'))
    [IgnoreRule(pattern_glob='/base_dir/**/test', ...)]

    >>> # test relative to gitignore file
    >>> get_rules_from_git_pattern(git_pattern='test/test2', path_base_dir=pathlib.Path('/base_dir/'))
    [IgnoreRule(pattern_glob='/base_dir/test/test2', ...)]

    >>> # Test Match Directories only - trailing slash sets match_file=False
    >>> get_rules_from_git_pattern(git_pattern='test/', path_base_dir=pathlib.Path('/base_dir/'))
    [IgnoreRule(pattern_glob='/base_dir/**/test', ..., match_file=False, ...)]

    >>> # The "/**" suffix matches the contents only (not the directory itself)
    >>> get_rules_from_git_pattern(git_pattern='test/**', path_base_dir=pathlib.Path('/base_dir/'))
    [IgnoreRule(pattern_glob='/base_dir/test/**/*', ...)]


    """
    emit_self_rule = True
    emit_contents_rule = False

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
    git_pattern = collapse_asterisk_runs(git_pattern.lstrip("/"))

    if git_pattern.startswith("**/"):
        match_anchored = False
        git_pattern = git_pattern[3:]

    if git_pattern.endswith("/**"):
        # "abc/**" matches everything *inside* abc, but not abc itself: emit only
        # the contents rule, never a rule that matches the directory abc.
        match_file = False
        emit_self_rule = False
        emit_contents_rule = True
        git_pattern = git_pattern[:-3]

    l_ignore_rules = create_rule_variations(
        pattern=git_pattern,
        pattern_original=pattern_original,
        path_base_dir=path_base_dir,
        match_file=match_file,
        emit_contents_rule=emit_contents_rule,
        match_anchored=match_anchored,
        is_negation_rule=is_negation_rule,
        source_file=path_source_file,
        source_line_number=source_line_number,
        emit_self_rule=emit_self_rule,
    )

    return l_ignore_rules


def collapse_asterisk_runs(git_pattern: str) -> str:
    """
    Git reads a path segment made only of three or more asterisks as ``**``.

    >>> collapse_asterisk_runs('***/foo')
    '**/foo'
    >>> collapse_asterisk_runs('a/****/b')
    'a/**/b'
    >>> collapse_asterisk_runs('a***b/c')
    'a***b/c'
    """
    segments = git_pattern.split("/")
    return "/".join("**" if seg.startswith("***") and not seg.strip("*") else seg for seg in segments)


def git_pattern_handle_blanks(git_pattern: str) -> str:
    """
    Trailing spaces are ignored unless they are quoted with backslash ("\").
    in fact all spaces in gitignore CAN be escaped.
    wcmatch.glob.globmatch supports both forms.

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

    If there is a separator at the beginning or middle (or both) of the
    pattern, then the pattern is relative to the directory level of the
    particular .gitignore file itself. Otherwise the pattern may also match at
    any level below the .gitignore level.

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
    If there is a separator at the end of the pattern then the pattern will
    match directories and their contents, otherwise the pattern can match both
    files and directories.

    >>> assert get_match_files('')
    >>> assert get_match_files('/something')
    >>> assert get_match_files('/some/thing')
    >>> assert not get_match_files('/some/thing/')
    """
    return not git_pattern.endswith("/")


def create_rule_variations(
    *,
    pattern: str,
    pattern_original: str,
    path_base_dir: pathlib.Path,
    match_file: bool,
    emit_contents_rule: bool,
    match_anchored: bool,
    is_negation_rule: bool,
    source_file: pathlib.Path | None,
    source_line_number: int | None,
    emit_self_rule: bool = True,
) -> list[IgnoreRule]:
    """
    create the variations of the rules, based on the parsed git line

    >>> path_base = pathlib.Path(__file__).parent.resolve()

    """
    # the directory is matched literally: "a[1]" must not act as a character class
    str_path_base_dir = wcmatch.glob.escape(str(path_base_dir).replace("\\", "/"))
    l_rules: list[IgnoreRule] = list()

    if match_anchored:
        pattern_resolved = str_path_base_dir + "/" + pattern
    else:
        pattern_resolved = str_path_base_dir + "/**/" + pattern

    if emit_self_rule:
        rule_match_file = IgnoreRule(
            pattern_glob=pattern_resolved,
            pattern_original=pattern_original,
            is_negation_rule=is_negation_rule,
            match_file=match_file,
            source_file=source_file,
            source_line_number=source_line_number,
        )
        l_rules.append(rule_match_file)

    if emit_contents_rule:
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


if __name__ == "__main__":
    print(
        b'this is a library only, the executable is named "igittigitt"',
        file=sys.stderr,
    )
