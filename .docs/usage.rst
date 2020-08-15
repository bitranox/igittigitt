- init the Ignore Parser

.. include:: ../igittigitt/igittigitt.py
    :code: python
    :start-after: # IgnoreParser{{{
    :end-before:  # IgnoreParser}}}

.. include:: ../tests/test_pytest.py
    :code: python
    :start-after: # IgnoreParserExamples{{{
    :end-before:  # IgnoreParserExamples}}}

--------------------------------

- add rules by rule files (the default method)

.. include:: ../igittigitt/igittigitt.py
    :code: python
    :start-after: # parse_rule_files{{{
    :end-before:  # parse_rule_files}}}


.. code-block:: python

    >>> # import all .gitignore recursively from base directory
    >>> ignore_parser.parse_rule_files(base_dir=path_source_dir)

    >>> # import all .gitignore recursively from base directory
    >>> # use another rule filename
    >>> ignore_parser.parse_rule_files(base_dir=path_source_dir, filename='my_ignore_rules')

--------------------------------

- add a rule by string

.. include:: ../igittigitt/igittigitt.py
    :code: python
    :start-after: # add_rule{{{
    :end-before:  # add_rule}}}

.. include:: ../tests/test_pytest.py
    :code: python
    :start-after: # add_rule_Example{{{
    :end-before:  # add_rule_Example}}}

--------------------------------

- match a file

.. include:: ../igittigitt/igittigitt.py
    :code: python
    :start-after: # match{{{
    :end-before:  # match}}}

--------------------------------

- shutil ignore function

.. include:: ../igittigitt/igittigitt.py
    :code: python
    :start-after: # shutil_ignore{{{
    :end-before:  # shutil_ignore}}}

.. include:: ../tests/test_pytest.py
    :code: python
    :start-after: # test_shutil_ignore_function_Example{{{
    :end-before:  # test_shutil_ignore_function_Example}}}
