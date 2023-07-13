- Before You start, its highly recommended to update pip and setup tools:


.. code-block::

    python -m pip --upgrade pip
    python -m pip --upgrade setuptools


.. include:: ./installation_via_pypi.rst

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


.. include:: ./installation_via_makefile.rst
