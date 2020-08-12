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
