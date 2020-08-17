================
centra-py-client
================


.. image:: https://img.shields.io/pypi/v/centra_py_client.svg
        :target: https://pypi.python.org/pypi/centra_py_client

.. image:: https://img.shields.io/travis/guardicode/centra_py_client.svg
        :target: https://travis-ci.com/guardicode/centra_py_client

.. image:: https://readthedocs.org/projects/centra-py-client/badge/?version=latest
        :target: https://centra-py-client.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Python client for Centra API access. Visit Guardicore_'s website for more information about Centra!

Find the full client documentation at https://centra-py-client.readthedocs.io (locally, `/docs` folder).

======================
Quick start guide
======================

============
Installation
============


Released version
----------------

To install centra-py-client, run this command in your terminal:

.. code-block:: console

    $ pip install centra_py_client

This is the preferred method to install centra-py-client, as it will always install the most recent released version.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for centra-py-client can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/guardicode/centra_py_client

Or download the `tarball`_:

.. code-block:: console

    $ curl -OJL https://github.com/guardicode/centra_py_client/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/guardicode/centra_py_client
.. _tarball: https://github.com/guardicode/centra_py_client/tarball/master


=====
Usage
=====

First, create a CentraClient::

    from centra_py_client import CentraClient, CentraSession
    client = CentraClient(CentraSession("my.centra.address", "username", "password"))

Then use the client to interact with Centra, e.g.::

    client.delete_label_by_name("Environemnt: TemporaryEnv")

======================
Stability status
======================

This package is currently considered unstable and there is no backward compatibility guaranteed.

This status will continue as long as the package is in the 0.x.y versions. When the package
stabilizes and we can guarantee backward compatibility, version 1.0.0 will be released.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _Guardicore: https://guardicore.com
