igittigitt
==========


Version v2.1.3 as of 2023-07-13 see `Changelog`_

|build_badge| |license| |jupyter| |pypi| |pypi-downloads| |black|

|codecov| |cc_maintain| |cc_issues| |cc_coverage| |snyk|



.. |build_badge| image:: https://github.com/bitranox/igittigitt/actions/workflows/python-package.yml/badge.svg
   :target: https://github.com/bitranox/igittigitt/actions/workflows/python-package.yml


.. |license| image:: https://img.shields.io/github/license/webcomics/pywine.svg
   :target: http://en.wikipedia.org/wiki/MIT_License

.. |jupyter| image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/bitranox/igittigitt/master?filepath=igittigitt.ipynb

.. for the pypi status link note the dashes, not the underscore !
.. |pypi| image:: https://img.shields.io/pypi/status/igittigitt?label=PyPI%20Package
   :target: https://badge.fury.io/py/igittigitt

.. |codecov| image:: https://img.shields.io/codecov/c/github/bitranox/igittigitt
   :target: https://codecov.io/gh/bitranox/igittigitt

.. |cc_maintain| image:: https://img.shields.io/codeclimate/maintainability-percentage/bitranox/igittigitt?label=CC%20maintainability
   :target: https://codeclimate.com/github/bitranox/igittigitt/maintainability
   :alt: Maintainability

.. |cc_issues| image:: https://img.shields.io/codeclimate/issues/bitranox/igittigitt?label=CC%20issues
   :target: https://codeclimate.com/github/bitranox/igittigitt/maintainability
   :alt: Maintainability

.. |cc_coverage| image:: https://img.shields.io/codeclimate/coverage/bitranox/igittigitt?label=CC%20coverage
   :target: https://codeclimate.com/github/bitranox/igittigitt/test_coverage
   :alt: Code Coverage

.. |snyk| image:: https://snyk.io/test/github/bitranox/igittigitt/badge.svg
   :target: https://snyk.io/test/github/bitranox/igittigitt

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/igittigitt
   :target: https://pypi.org/project/igittigitt/
   :alt: PyPI - Downloads

- A spec-compliant gitignore parser for Python.
- IgittIgitt provides methods to intentionally ignore files and directories (usually to copy or distribute them).
- The patterns to define what should be ignored, are stored in "ignore" files, which are compatible with `git <https://git-scm.com/docs/gitignore#_pattern_format>`_.


Limitations
-----------

- at the current stage the parser is ok, as long as You dont use negations (ignore globs, which starts with "!")
- precedence levels are not supported correctly
- according to the manual,  more nested ignore files have a higher precedence than less nested ignore files - this is currently
  neither checked, nor supported correctly.
- sizelimit, hidden directories and other features might behave different from git
- some features are not implemented
- the limitations are somehow a result of the incomplete documentation at `git-scm.com <https://git-scm.com/docs/gitignore#_pattern_format>`_
- luckily there is a good explanation at `WalkBuilder <https://docs.rs/ignore/0.4.18/ignore/struct.WalkBuilder.html>`_ , so You can expect things
  will get better over time

is it still useful ?
--------------------
- yes
- if You dont need negation rules, and dont rely on correct precedence of nested rule files, it will work just fine


Ignore rules - correct handling (currently not)
-----------------------------------------------
There are many rules that influence whether a particular file or directory is skipped.
Those rules are documented here. Note that the rules assume a default configuration.

1) glob overrides are checked. If a path matches a glob override, then matching stops.
    - The path is then only skipped if the glob that matched the path is an ignore glob.
      (An override glob is a whitelist glob unless it starts with a !, in which case it is an ignore glob.)

2) ignore files are checked.
    - Ignore files currently only come from git ignore files
      (.gitignore, .git/info/exclude and the configured global gitignore file),
      plain .ignore files, which have the same format as gitignore files, or explicitly added ignore files.
    - The precedence order is: .ignore, .gitignore, .git/info/exclude, global gitignore and finally
      explicitly added ignore files.
    - Note that precedence between different types of ignore files is not impacted by the directory hierarchy;
      any .ignore file overrides all .gitignore files.
    - Within each precedence level, more nested ignore files have a higher precedence than less nested
      ignore files. (really ? check !)

3)  - if the previous step yields an ignore match, then all matching is stopped and the path is skipped.
    - if it yields a whitelist match, then matching continues, a whitelist match can be overridden by a later matcher.

4)  - unless the path is a directory, the file type matcher is run on the path.
    - as above, if it yields an ignore match, then all matching is stopped and the path is skipped.
    - if it yields a whitelist match, then matching continues.

5)  - if the path has not been whitelisted and it is hidden, then the path is skipped.

6)  - unless the path is a directory, the size of the file is compared against the max filesize limit.
      If it exceeds the limit, it is skipped.


Ignore rules - current handling (not spec compliant)
----------------------------------------------------

- no precedence levels are supported, rules are just sorted by length (which is terribly wrong if negation rules are used)
- all other points from above are not implemented


After reading (nesting supported) the `.gitignore` file, You can match files against the parsers match function. If the file should be ignored, it matches.
We also provide an ignore function for `shutil.treecopy` so it is easy just to copy a directory tree without the files which should be ignored.
A `match` indicates, that the file should be ignored.

Suppose `/home/bitranox/project/.gitignore` contains the following:

.. code-block:: python

    # /home/bitranox/project/.gitignore
    __pycache__/
    *.py[cod]


Then:

.. code-block:: python

    >>> import igittigitt
    >>> parser = igittigitt.IgnoreParser()
    >>> parser.parse_rule_file(pathlib.Path('/home/bitranox/project/.gitignore'))
    >>> parser.match(pathlib.Path('/home/bitranox/project/main.py'))
    False
    >>> parser.match(pathlib.Path('/home/bitranox/project/main.pyc'))
    True
    >>> parser.match(pathlib.Path('/home/bitranox/project/dir/main.pyc'))
    True
    >>> parser.match(pathlib.Path('/home/bitranox/project/__pycache__'))
    True
    # copy the tree without the files which should be ignored by .gitignore
    >>> shutil.copytree('/home/bitranox/project', '/home/bitranox/project2', ignore=parser.shutil_ignore)


Default Patterns
----------------
Patterns which a user wants Git to ignore in all situations (e.g., backup or temporary files generated by
the user’s editor of choice) can be put in a file, which location is configured via environment variables :

POSIX :
Its default value is $XDG_CONFIG_HOME/git/ignore. If $XDG_CONFIG_HOME is either not set or empty, $HOME/.config/git/ignore is used instead.

WINDOWS :
Its default value is %XDG_CONFIG_HOME%/git/ignore. If %XDG_CONFIG_HOME% is either not set or empty, %HOME%/.config/git/ignore is used instead.
If %HOME% is either not set or empty, %USERPROFILE%/git/ignore is used instead.

The Usage of the default Pattern can be disabled by setting `conf_igittigitt.add_default_patterns=False`

Motivation
----------
I couldn't find a good library for doing the above on PyPI. There are
several other libraries, but they don't seem to support all features,
be it the square brackets in `*.py[cod]` or top-level paths `/...`.

inspired by https://github.com/mherrmann/gitignore_parser but in fact I needed to
throw away almost everything, because of serious matching bugs and unmaintainable spaghetti code.


igittigitt
----------
- meaning (german):
    often perceived as an exaggeration exclamation of rejection, rejection full of disgust, disgust (mostly used by young children)
- synonyms:
    ugh, brr, ugh devil, yuck
- origin
    probably covering for: o God, ogottogott

----

automated tests, Github Actions, Documentation, Badges, etc. are managed with `PizzaCutter <https://github
.com/bitranox/PizzaCutter>`_ (cookiecutter on steroids)

Python version required: 3.8.0 or newer

tested on recent linux with python 3.8, 3.9, 3.10, 3.11, pypy-3.9 - architectures: amd64

`100% code coverage <https://codeclimate.com/github/bitranox/igittigitt/test_coverage>`_, flake8 style checking ,mypy static type checking ,tested under `Linux, macOS, Windows <https://github.com/bitranox/igittigitt/actions/workflows/python-package.yml>`_, automatic daily builds and monitoring

----

- `Try it Online`_
- `Usage`_
- `Usage from Commandline`_
- `Installation and Upgrade`_
- `Requirements`_
- `Acknowledgements`_
- `Contribute`_
- `Report Issues <https://github.com/bitranox/igittigitt/blob/master/ISSUE_TEMPLATE.md>`_
- `Pull Request <https://github.com/bitranox/igittigitt/blob/master/PULL_REQUEST_TEMPLATE.md>`_
- `Code of Conduct <https://github.com/bitranox/igittigitt/blob/master/CODE_OF_CONDUCT.md>`_
- `License`_
- `Changelog`_

----

Try it Online
-------------

You might try it right away in Jupyter Notebook by using the "launch binder" badge, or click `here <https://mybinder.org/v2/gh/{{rst_include.
repository_slug}}/master?filepath=igittigitt.ipynb>`_

Usage
-----------

- init the Ignore Parser

.. code-block:: python

    class IgnoreParser(object):
        def __init__(self) -> None:
            """
            init the igittigitt parser.
            """

.. code-block:: python

        >>> # init as normal Instance
        >>> parser = igittigitt.IgnoreParser()
        >>> print(parser)
        <...IgnoreParser object at ...>

        >>> # init with context manager
        >>> with igittigitt.IgnoreParser() as parser:
        ...     print(parser)
        <...IgnoreParser object at ...>

--------------------------------

- add rules by rule files (the default method)

.. code-block:: python

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

.. code-block:: python

    >>> # import all .gitignore recursively from base directory
    >>> ignore_parser.parse_rule_files(base_dir=path_source_dir)

    >>> # import all .gitignore recursively from base directory
    >>> # use another rule filename
    >>> ignore_parser.parse_rule_files(base_dir=path_source_dir, filename='my_ignore_rules')

--------------------------------

- add a rule by string

.. code-block:: python

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

.. code-block:: python

        >>> parser = igittigitt.IgnoreParser()
        >>> parser.add_rule('*.py[cod]', base_path='/home/bitranox')

--------------------------------

- match a file

.. code-block:: python

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

--------------------------------

- shutil ignore function

.. code-block:: python

        def shutil_ignore(self, base_dir: str, file_names: List[str]) -> Set[str]:
            """
            Ignore function for shutil.copy_tree
            """

.. code-block:: python

        >>> path_source_dir = path_test_dir / "example"
        >>> path_target_dir = path_test_dir / "target"
        >>> ignore_parser = igittigitt.IgnoreParser()
        >>> ignore_parser.parse_rule_files(base_dir=path_source_dir, filename=".test_gitignore")
        >>> discard = shutil.copytree(path_source_dir, path_target_dir, ignore=ignore_parser.shutil_ignore)

Usage from Commandline
------------------------

.. code-block::

   Usage: igittigitt [OPTIONS] COMMAND [ARGS]...

     A spec-compliant gitignore parser for Python

   Options:
     --version                     Show the version and exit.
     --traceback / --no-traceback  return traceback information on cli
     -h, --help                    Show this message and exit.

   Commands:
     info  get program informations

Installation and Upgrade
------------------------

- Before You start, its highly recommended to update pip and setup tools:


.. code-block::

    python -m pip --upgrade pip
    python -m pip --upgrade setuptools

- to install the latest release from PyPi via pip (recommended):

.. code-block::

    python -m pip install --upgrade igittigitt


- to install the latest release from PyPi via pip, including test dependencies:

.. code-block::

    python -m pip install --upgrade igittigitt[test]

- to install the latest version from github via pip:


.. code-block::

    python -m pip install --upgrade git+https://github.com/bitranox/igittigitt.git


- include it into Your requirements.txt:

.. code-block::

    # Insert following line in Your requirements.txt:
    # for the latest Release on pypi:
    igittigitt

    # for the latest development version :
    igittigitt @ git+https://github.com/bitranox/igittigitt.git

    # to install and upgrade all modules mentioned in requirements.txt:
    python -m pip install --upgrade -r /<path>/requirements.txt


- to install the latest development version, including test dependencies from source code:

.. code-block::

    # cd ~
    $ git clone https://github.com/bitranox/igittigitt.git
    $ cd igittigitt
    python -m pip install -e .[test]

- via makefile:
  makefiles are a very convenient way to install. Here we can do much more,
  like installing virtual environments, clean caches and so on.

.. code-block:: shell

    # from Your shell's homedirectory:
    $ git clone https://github.com/bitranox/igittigitt.git
    $ cd igittigitt

    # to run the tests:
    $ make test

    # to install the package
    $ make install

    # to clean the package
    $ make clean

    # uninstall the package
    $ make uninstall

Requirements
------------
following modules will be automatically installed :

.. code-block:: bash

    ## Project Requirements
    attrs
    click
    cli_exit_tools
    lib_detect_testenv
    wcmatch

Acknowledgements
----------------

- special thanks to "uncle bob" Robert C. Martin, especially for his books on "clean code" and "clean architecture"

Contribute
----------

I would love for you to fork and send me pull request for this project.
- `please Contribute <https://github.com/bitranox/igittigitt/blob/master/CONTRIBUTING.md>`_

License
-------

This software is licensed under the `MIT license <http://en.wikipedia.org/wiki/MIT_License>`_

---

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

