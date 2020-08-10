================
centra-py-client
================


.. image:: https://img.shields.io/pypi/v/centra_py_client.svg
        :target: https://pypi.python.org/pypi/centra_py_client

.. image:: https://img.shields.io/travis/yonatang93/centra_py_client.svg
        :target: https://travis-ci.com/yonatang93/centra_py_client

.. image:: https://readthedocs.org/projects/centra-py-client/badge/?version=latest
        :target: https://centra-py-client.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Python client for Centra API access.


* Free software: GNU General Public License v3
* Documentation: https://centra-py-client.readthedocs.io.


Quick start
-----------

Installation
^^^^^^^^^^^^

From Pypi::

    pip install centra_py_client

From source::

    git clone <GIT_URL_HERE>
    cd centra_py_client
    python setup.py install

Usage
^^^^^^^^^^^^

First, create a CentraClient::

    from centra_py_client import CentraClient, CentraSession
    client = CentraClient(CentraSession("my.centra.address", "username", "password"))

Then use the client to interact with Centra, e.g.::

    client.delete_label_by_name("Environemnt: TemporaryEnv")

Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
