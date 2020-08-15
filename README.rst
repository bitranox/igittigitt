igittigitt
==========


Version v2.0.0 as of 2020-08-16 see `Changelog`_

|travis_build| |license| |jupyter| |pypi| |black|

|codecov| |better_code| |cc_maintain| |cc_issues| |cc_coverage| |snyk|


.. |travis_build| image:: https://img.shields.io/travis/bitranox/igittigitt/master.svg
   :target: https://travis-ci.org/bitranox/igittigitt

.. |license| image:: https://img.shields.io/github/license/webcomics/pywine.svg
   :target: http://en.wikipedia.org/wiki/MIT_License

.. |jupyter| image:: https://mybinder.org/badge_logo.svg
 :target: https://mybinder.org/v2/gh/bitranox/igittigitt/master?filepath=igittigitt.ipynb

.. for the pypi status link note the dashes, not the underscore !
.. |pypi| image:: https://img.shields.io/pypi/status/igittigitt?label=PyPI%20Package
   :target: https://badge.fury.io/py/igittigitt

.. |codecov| image:: https://img.shields.io/codecov/c/github/bitranox/igittigitt
   :target: https://codecov.io/gh/bitranox/igittigitt

.. |better_code| image:: https://bettercodehub.com/edge/badge/bitranox/igittigitt?branch=master
   :target: https://bettercodehub.com/results/bitranox/igittigitt

.. |cc_maintain| image:: https://img.shields.io/codeclimate/maintainability-percentage/bitranox/igittigitt?label=CC%20maintainability
   :target: https://codeclimate.com/github/bitranox/igittigitt/maintainability
   :alt: Maintainability

.. |cc_issues| image:: https://img.shields.io/codeclimate/issues/bitranox/igittigitt?label=CC%20issues
   :target: https://codeclimate.com/github/bitranox/igittigitt/maintainability
   :alt: Maintainability

.. |cc_coverage| image:: https://img.shields.io/codeclimate/coverage/bitranox/igittigitt?label=CC%20coverage
   :target: https://codeclimate.com/github/bitranox/igittigitt/test_coverage
   :alt: Code Coverage

.. |snyk| image:: https://img.shields.io/snyk/vulnerabilities/github/bitranox/igittigitt
   :target: https://snyk.io/test/github/bitranox/igittigitt

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

A spec-compliant gitignore parser for Python

after reading (nesting supported) the `.gitignore` file, You can match files against the parsers match function. If the file should be ignored, it matches.

We also provide an ignore function for `shutil.treecopy` so it is easy just to copy a directory tree without the files which should be ignored.

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

automated tests, Travis Matrix, Documentation, Badges, etc. are managed with `PizzaCutter <https://github
.com/bitranox/PizzaCutter>`_ (cookiecutter on steroids)

Python version required: 3.6.0 or newer

tested on linux "bionic" with python 3.6, 3.7, 3.8, 3.8-dev, pypy3 - architectures: amd64, ppc64le, s390x, arm64

`100% code coverage <https://codecov.io/gh/bitranox/igittigitt>`_, flake8 style checking ,mypy static type checking ,tested under `Linux, macOS, Windows <https://travis-ci.org/bitranox/igittigitt>`_, automatic daily builds and monitoring

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

.. code-block:: bash

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


.. code-block:: bash

    python -m pip --upgrade pip
    python -m pip --upgrade setuptools

- to install the latest release from PyPi via pip (recommended):

.. code-block:: bash

    python -m pip install --upgrade igittigitt

- to install the latest version from github via pip:


.. code-block:: bash

    python -m pip install --upgrade git+https://github.com/bitranox/igittigitt.git


- include it into Your requirements.txt:

.. code-block:: bash

    # Insert following line in Your requirements.txt:
    # for the latest Release on pypi:
    igittigitt

    # for the latest development version :
    igittigitt @ git+https://github.com/bitranox/igittigitt.git

    # to install and upgrade all modules mentioned in requirements.txt:
    python -m pip install --upgrade -r /<path>/requirements.txt


- to install the latest development version from source code:

.. code-block:: bash

    # cd ~
    $ git clone https://github.com/bitranox/igittigitt.git
    $ cd igittigitt
    python setup.py install

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

