Changelog
=========

- new MAJOR version for incompatible API changes,
- new MINOR version for added functionality in a backwards compatible manner
- new PATCH version for backwards compatible bug fixes

TODO:
    - code coverage
    - test context manager
    - add nested .gitignore files
    - __ALL__= ...
    - documentation
    - asserts for __ALL__ parameters

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
