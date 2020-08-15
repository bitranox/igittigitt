Changelog
=========

- new MAJOR version for incompatible API changes,
- new MINOR version for added functionality in a backwards compatible manner
- new PATCH version for backwards compatible bug fixes

TODO:
    - code coverage
    - add nested .gitignore files
    - documentation

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
