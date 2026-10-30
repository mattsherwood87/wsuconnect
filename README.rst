wsuconnect
==========

Data management and analysis tools for Wright State University's Center of Neuroimaging and
Neuro-Evaluation of Cognitive Technologies (CoNNECT), which houses a Philips Ingenia Cx 3T MRI scanner.

The ``wsuconnect`` package moves MRI data from the scanner to centralized storage buckets, organizes it in
the `Brain Imaging Data Structure (BIDS) <https://bids-specification.readthedocs.io/>`__, keeps a MySQL
database of source and raw data files, and runs processing pipelines on the CoNNECT Neuroimaging Processing
Cluster (NPC) through HTCondor.

Documentation
-------------

The CoNNECT manual is on Read the Docs:

https://connect-tutorial.readthedocs.io/en/latest/

It covers administration, MRI scheduling, the systems overview, cluster computing, processing procedures,
the support tools reference, and the project-specific JSON control files.

Repository layout
-----------------

``wsuconnect/``
    The Python package. The ``connect_*.py`` scripts are the command-line programs.
``wsuconnect/support_tools/``
    Functions the scripts are built on, including BIDS naming, MySQL, HTCondor job creation, and
    processing workflows.
``wsuconnect/classes/``
    Shared classes, such as the credentials reader.
``wsuconnect/data/``
    Package data, including ``credentials.json`` (project settings) and ``connect_bids_config.json``.
``docs/``
    Sphinx source for the Read the Docs manual.

Requirements
------------

- An NPC node running Ubuntu 24.04, with access to the HTCondor pool and the centralized storage bucket mounts.
- Python 3.12 or newer.
- Docker, for jobs that run in HTCondor's Docker universe. Other jobs run in the vanilla universe as Python or
  bash.
- A FreeSurfer license file in the package's ``licenses/`` folder. It is not tracked in git.

Installation
------------

.. code-block:: console

    git clone https://github.com/mattsherwood87/wsuconnect.git
    cd wsuconnect
    pip install .

Building the documentation locally
----------------------------------

.. code-block:: console

    pip install -r docs/source/requirements.txt
    sphinx-build -b html docs/source docs/build/html

Read the Docs rebuilds the manual from ``main`` using ``.readthedocs.yaml``.

License
-------

CC0 1.0 Universal. See ``LICENSE``.
