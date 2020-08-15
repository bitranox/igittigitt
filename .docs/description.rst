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
