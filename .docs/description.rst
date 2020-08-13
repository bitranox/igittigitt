A spec-compliant gitignore parser for Python

forked from https://github.com/mherrmann/gitignore_parser we might join later ....


Suppose `/home/michael/project/.gitignore` contains the following:

.. code-block:: python

    # /home/michael/project/.gitignore
    __pycache__/
    *.py[cod]



Then:

.. code-block:: python

    >>> import igittigitt
    >>> parser = igittigitt.IgnoreParser()
    >>> parser.parse_rule_file(pathlib.Path('/home/michael/project/.gitignore'))
    >>> parser.match(pathlib.Path('/home/michael/project/main.py'))
    False
    >>> parser.match(pathlib.Path('/home/michael/project/main.pyc'))
    True
    >>> parser.match(pathlib.Path('/home/michael/project/dir/main.pyc'))
    True
    >>> parser.match(pathlib.Path('/home/michael/project/__pycache__'))
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
    ugh, brr, ugh devil, yuck
- origin
    probably covering for: o God, ogottogott
