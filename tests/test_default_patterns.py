"""Which user-level ignore file is read (``_add_default_patterns``), as git chooses it.

The rule, measured against git 2.56.0.windows.3 and git on Linux: ``$XDG_CONFIG_HOME/git/ignore``
when ``XDG_CONFIG_HOME`` is set, otherwise ``.config/git/ignore`` under git's home directory.
git's home is ``HOME``; on Windows, when ``HOME`` is unset, it is ``HOMEDRIVE`` + ``HOMEPATH`` if
that directory exists, and otherwise ``USERPROFILE``. ``USERDATA`` is never read.

Each test sets the environment for itself and writes one ignore file per candidate location,
then asserts which of those files the rules came from.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, cast

import pytest
from pydantic import ValidationError

import igittigitt

if TYPE_CHECKING:
    from pathlib import Path

_LOOKUP_VARIABLES = ("XDG_CONFIG_HOME", "HOME", "HOMEDRIVE", "HOMEPATH", "USERPROFILE", "USERDATA")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in _LOOKUP_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _ignore_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("*.log\n", encoding="utf-8")
    return path


def _home_ignore(home: Path) -> Path:
    return _ignore_file(home / ".config" / "git" / "ignore")


def _set_homedrive_homepath(env: pytest.MonkeyPatch, directory: Path) -> None:
    # git concatenates the two as plain strings ("C:" + "\\Users\\me"), so any split of the
    # path into a prefix and the rest names the same directory.
    text = str(directory)
    env.setenv("HOMEDRIVE", text[:2])
    env.setenv("HOMEPATH", text[2:])


def _sources(tmp_path: Path, *, is_windows: bool) -> set[Path]:
    parser = igittigitt.IgnoreParser()
    parser._add_default_patterns(path_base_dir=tmp_path, is_windows=is_windows)
    return {rule.source_file for rule in parser.rules if rule.source_file is not None}


@pytest.mark.parametrize("is_windows", [False, True])
def test_nothing_set_reads_no_user_ignore_file(clean_env: pytest.MonkeyPatch, tmp_path: Path, is_windows: bool) -> None:
    assert _sources(tmp_path, is_windows=is_windows) == set()


@pytest.mark.parametrize("is_windows", [False, True])
def test_xdg_config_home_wins_over_home(clean_env: pytest.MonkeyPatch, tmp_path: Path, is_windows: bool) -> None:
    xdg_file = _ignore_file(tmp_path / "xdg" / "git" / "ignore")
    _home_ignore(tmp_path / "home")
    clean_env.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    clean_env.setenv("HOME", str(tmp_path / "home"))

    assert _sources(tmp_path, is_windows=is_windows) == {xdg_file}


@pytest.mark.parametrize("is_windows", [False, True])
def test_home_is_used_when_xdg_config_home_is_unset(
    clean_env: pytest.MonkeyPatch, tmp_path: Path, is_windows: bool
) -> None:
    home_file = _home_ignore(tmp_path / "home")
    _home_ignore(tmp_path / "profile")
    clean_env.setenv("HOME", str(tmp_path / "home"))
    clean_env.setenv("USERPROFILE", str(tmp_path / "profile"))

    assert _sources(tmp_path, is_windows=is_windows) == {home_file}


def test_an_empty_xdg_config_home_counts_as_unset(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # An empty XDG_CONFIG_HOME must fall through to HOME, never to "./git/ignore".
    home_file = _home_ignore(tmp_path / "home")
    _ignore_file(tmp_path / "git" / "ignore")
    clean_env.setenv("XDG_CONFIG_HOME", "")
    clean_env.setenv("HOME", str(tmp_path / "home"))
    clean_env.chdir(tmp_path)

    assert _sources(tmp_path, is_windows=False) == {home_file}


def test_windows_without_home_reads_userprofile(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile_file = _home_ignore(tmp_path / "profile")
    clean_env.setenv("USERPROFILE", str(tmp_path / "profile"))

    assert _sources(tmp_path, is_windows=True) == {profile_file}


def test_windows_homedrive_homepath_wins_over_userprofile(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    drive_file = _home_ignore(tmp_path / "drivehome")
    _home_ignore(tmp_path / "profile")
    _set_homedrive_homepath(clean_env, tmp_path / "drivehome")
    clean_env.setenv("USERPROFILE", str(tmp_path / "profile"))

    assert _sources(tmp_path, is_windows=True) == {drive_file}


def test_windows_homedrive_homepath_that_is_no_directory_falls_back_to_userprofile(
    clean_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_file = _home_ignore(tmp_path / "profile")
    _set_homedrive_homepath(clean_env, tmp_path / "missing")
    clean_env.setenv("USERPROFILE", str(tmp_path / "profile"))

    assert _sources(tmp_path, is_windows=True) == {profile_file}


@pytest.mark.os_posix
def test_windows_homedrive_homepath_that_cannot_be_examined_falls_back_to_userprofile(
    clean_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Path.is_dir() re-raises the permission error before Python 3.14; git treats a path it
    # cannot stat as no directory and moves on to USERPROFILE.
    if sys.platform != "win32" and os.geteuid() == 0:
        pytest.skip("root reads past directory permissions")
    profile_file = _home_ignore(tmp_path / "profile")
    locked = tmp_path / "locked"
    _home_ignore(locked / "drivehome")
    _set_homedrive_homepath(clean_env, locked / "drivehome")
    clean_env.setenv("USERPROFILE", str(tmp_path / "profile"))
    locked.chmod(0)
    try:
        assert _sources(tmp_path, is_windows=True) == {profile_file}
    finally:
        locked.chmod(0o700)


@pytest.mark.parametrize(("knob", "expected_user_rules"), [(True, 1), (False, 0)])
def test_parse_rule_files_follows_conf_igittigitt_at_call_time(
    clean_env: pytest.MonkeyPatch, tmp_path: Path, knob: bool, expected_user_rules: int
) -> None:
    # conf_igittigitt is the public runtime configuration: changing it after import must
    # change what parse_rule_files does when the caller does not pass add_default_patterns.
    user_file = _ignore_file(tmp_path / "xdg" / "git" / "ignore")
    clean_env.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    clean_env.setattr(igittigitt.conf_igittigitt, "add_default_patterns", knob)
    (tmp_path / "project").mkdir()
    parser = igittigitt.IgnoreParser()

    parser.parse_rule_files(tmp_path / "project")

    assert sum(rule.source_file == user_file for rule in parser.rules) == expected_user_rules


@pytest.mark.parametrize("value", ["no", 0, None])
def test_conf_igittigitt_refuses_a_non_bool_add_default_patterns(value: object) -> None:
    conf = igittigitt.conf_igittigitt.__class__()

    with pytest.raises(ValidationError):
        # The cast is the point of the test: a value of the wrong type reaching the setter.
        conf.add_default_patterns = cast("bool", value)


@pytest.mark.parametrize("is_windows", [False, True])
def test_userdata_is_never_read(clean_env: pytest.MonkeyPatch, tmp_path: Path, is_windows: bool) -> None:
    _ignore_file(tmp_path / "userdata" / "git" / "ignore")
    clean_env.setenv("USERDATA", str(tmp_path / "userdata"))

    assert _sources(tmp_path, is_windows=is_windows) == set()


def test_off_windows_only_home_names_the_home_directory(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _home_ignore(tmp_path / "profile")
    _home_ignore(tmp_path / "drivehome")
    _set_homedrive_homepath(clean_env, tmp_path / "drivehome")
    clean_env.setenv("USERPROFILE", str(tmp_path / "profile"))

    assert _sources(tmp_path, is_windows=False) == set()
