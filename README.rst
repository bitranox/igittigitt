igittigitt
==========


Version v0.0.1 as of 2020-08-12 see `Changelog`_

|travis_build| |license| |jupyter| |pypi|

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

A spec-compliant gitignore parser for Python

forked from https://github.com/mherrmann/gitignore_parser we might join later ....


.. code-block:: python

    Suppose `/home/michael/project/.gitignore` contains the following:
    __pycache__/
    *.py[cod]



Then:

.. code-block:: python

    >>> from gitignore_parser import parse_gitignore
    >>> matches = parse_gitignore('/home/michael/project/.gitignore')
    >>> matches('/home/michael/project/main.py')
    False
    >>> matches('/home/michael/project/main.pyc')
    True
    >>> matches('/home/michael/project/dir/main.pyc')
    True
    >>> matches('/home/michael/project/__pycache__')
    True


Motivation
----------
I couldn't find a good library for doing the above on PyPI. There are
several other libraries, but they don't seem to support all features,
be it the square brackets in `*.py[cod]` or top-level paths `/...`.

forked from https://github.com/mherrmann/gitignore_parser because I
need to move on faster ... we might join the projects again after stabilisation

igittigitt
----------
- meaning (german):
    often perceived as an exaggeration exclamation of rejection, rejection full of disgust, disgust (mostly used by young children)
- synonyms:
    ugh, brr, ugh devil
- origin
    probably covering for: o God, ogottogott

----

automated tests, Travis Matrix, Documentation, Badges, etc. are managed with `PizzaCutter <https://github
.com/bitranox/PizzaCutter>`_ (cookiecutter on steroids)

Python version required: 3.6.0 or newer

tested on linux "bionic" with python 3.6, 3.7, 3.8, 3.8-dev, pypy3 - architectures: amd64, ppc64le, s390x, arm64

`100% code coverage <https://codecov.io/gh/bitranox/igittigitt>`_, flake8 style checking ,tested under `Linux, macOS, Windows <https://travis-ci.org/bitranox/igittigitt>`_, automatic daily builds and monitoring

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

python methods:

.. code-block:: python

    def parse_gitignore(full_path, base_dir=None):
        """
        parse a git ignore file, create rules from a gitignore file

        Parameter
        ---------
        full_path
            the full path to the ignore file
        base_dir
            todo : good description missing

        """

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
    click
    cli_exit_tools @ git+https://github.com/bitranox/cli_exit_tools.git

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

v0.0.1
--------
2020-08-12: initial release
    - fork from https://github.com/mherrmann/gitignore_parser

