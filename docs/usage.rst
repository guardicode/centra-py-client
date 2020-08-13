=====
Usage
=====

First, create a CentraClient::

    from centra_py_client import CentraClient, CentraSession
    client = CentraClient(CentraSession("my.centra.address", "username", "password"))

Then use the client to interact with Centra, e.g.::

    client.delete_label_by_name("Environemnt: TemporaryEnv")

