Changelog
=========

- new MAJOR version for incompatible API changes,
- new MINOR version for added functionality in a backwards compatible manner
- new PATCH version for backwards compatible bug fixes

v2.1.3
---------
2023-07-13:
    - require minimum python 3.8
    - remove python 3.7 tests
    - introduce PEP517 packaging standard
    - introduce pyproject.toml build-system
    - remove setup.cfg
    - remove setup.py
    - update black config
    - clean ./tests/test_cli.py
    - update black config
    - remove travis config
    - remove bettercodehub config
    - do not upload .egg files to pypi.org
    - update github actions : checkout@v3 and setup-python@v4
    - remove "better code" badges
    - remove python 3.6 tests
    - adding python 3.11 tests
    - update pypy tests to 3.9

v2.1.2
-------
2022-06-25:
    - set __all__ accordingly
    - point out limitations in Readme
    - integrate github actions
    - adjusting tests: patterns ending with a point can not match on windows
    - removing invalid escape sequences
    - match on paths with symlinks in their components

v2.1.0
------
2021-11-18: minor release
    - issue 21, support default ignore files

v2.0.5
--------
2021-11-16: patch release
    - Issue 18, 22, support following symlinks

v2.0.4
--------
2020-11-15: patch release
    - Issue 16, support following symlinks

v2.0.3
--------
2020-10-09: service release
    - update travis build matrix for linux 3.9-dev
    - update travis build matrix (paths) for windows 3.9 / 3.10
    - bump up coverage

v2.0.2
--------
2020-09-20:
    - (again) correcting matching bug in subdirectories, added tests for that
    - use slotted class for rules, make it hashable and sortable
    - avoid creating duplicate rules for better performance

v2.0.1
--------
2020-09-18:
    - correct matching bug in subdirectories
    - avoid redundant patterns when match subdirectories

v2.0.0
--------
2020-08-14:
    - complete redesign
    - get rid of regexp matching
    - more tests
    - now correct matching in subdirs, directory names,
      filenames, etc ...

v1.0.6
--------
2020-08-14:
    - get rid of the named tuple
    - implement attrs
    - full typing, PEP561 package
    - add blacked badge

v1.0.5
--------
2020-08-14: fix Windows and MacOs tests

v1.0.4
--------
2020-08-13: handle trailing spaces

v1.0.3
--------
2020-08-13: handle comments

v1.0.2
--------
2020-08-13: handle directories

v1.0.1
--------
2020-08-13: fix negation handling


v1.0.0
--------
2020-08-13: change the API interface
    - put parser in a class to keep rules there
    - change tests to pytest
    - start type annotations
    - implement black codestyle

v0.0.1
--------
2020-08-12: initial release
    - fork from https://github.com/mherrmann/gitignore_parser
