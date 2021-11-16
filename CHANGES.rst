Changelog
=========

- new MAJOR version for incompatible API changes,
- new MINOR version for added functionality in a backwards compatible manner
- new PATCH version for backwards compatible bug fixes

v2.0.6b
--------
work in progress

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
