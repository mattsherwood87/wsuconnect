
.. _read_creds_python:

creds
=====

Data collected and produced for each project follow the `BIDS specification <https://bids-specification.readthedocs.io/en/stable/>`__ (see :ref:`data_organization`).

A single JSON file describes the parameters for each project. This file is ``credentials.json`` and is located in the wsuconnect package's ``data/`` directory
(``wsuconnect/data/credentials.json``). Each project in the credentials file is defined as its own key, named by the protocol number assigned by its IRB of
record. For pilot studies, a short name may be used in place of the IRB number.

.. _credentials_main_table:

.. list-table:: Top-level keys of the credentials.json file.
   :widths: 25 15 50
   :header-rows: 1

   * - **Key**
     - **Data Type**
     - **Description**
   * - projects
     - list[string]
     - List of all project identifiers (these are referred to as <project_identifier>)
   * - master_machine_name
     - list[string]
     - Name of the NPC master node
   * - <project_identifier>
     - dictionary
     - Dictionary identifying key elements of each project, described in :numref:`credentials_secondary_table`

|

.. _credentials_secondary_table:

.. list-table:: Dictionary keys for the <project_identifier> elements.
   :widths: 25 15 50
   :header-rows: 1

   * - **Key**
     - **Data Type**
     - **Description**
   * - description
     - string
     - Short description of the project
   * - title
     - string
     - Full project title
   * - database
     - string
     - MySQL database holding the project's searchTable and searchSourceTable (see :ref:`the MySQL section of this document <mysql_db>`)
   * - dataDir
     - string
     - Full path to the project folder on the local mount of the project's centralized storage bucket (``<storage_mount>/projects/<contract_year>_<funding_source>/<project_title>``)
   * - dicom_id
     - string
     - Unique string within the DICOM filenames to help identify DICOM images within the PACS and sourcedata directories
   * - examCardName
     - string
     - Name of the project's ExamCard on the MRI scanner
   * - instance_id
     - string
     - Not used (kept as an empty string)
   * - ipAddress
     - string
     - Not used (kept as an empty string)
   * - machineNames
     - list[string]
     - NPC nodes that may run the project's HTCondor jobs
   * - gpuMachineNames
     - list[string]
     - NPC GPU nodes that may run the project's GPU jobs
   * - project
     - string
     - The <project_identifier>, repeated inside the entry
   * - searchTable
     - string
     - MySQL table identifying files within the project's directory (excluding sourcedata)
   * - searchSourceTable
     - string
     - MySQL table identifying files within the project's sourcedata directory
   * - dockerMountIf
     - string
     - Name of the mounted storage bucket (resshare) to bind mount into Docker containers, such as ``resshare20``
   * - contact
     - list[string]
     - Email addresses of the project contacts
   * - simnibs
     - dictionary
     - Optional. SimNIBS charm + brain_print jobs submitted by connect_pacs_dicom_grabber.py, described in :numref:`credentials_simnibs_table`

|

.. _credentials_simnibs_table:

.. list-table:: Keys of the optional ``simnibs`` dictionary. Missing keys take the default; a project with no ``simnibs`` entry is disabled.
   :widths: 20 15 25 40
   :header-rows: 1

   * - **Key**
     - **Data Type**
     - **Default**
     - **Description**
   * - enabled
     - bool
     - false
     - Submit a charm job for each new subject/session
   * - condor_user
     - string
     - nw028mss
     - Non-root account that owns the HTCondor jobs (HTCondor will not run root jobs)
   * - t1_label
     - string
     - ""
     - Text right before ``_T1w`` in the BIDS filename, e.g. ``rec-axial``, to pick one orientation; empty = any T1w
   * - t2_label
     - string
     - ""
     - The same for ``_T2w``
   * - machines
     - list[string]
     - ["npc-core-gpu1"]
     - Execute hosts that have the SimNIBS image loaded (used instead of machineNames)
   * - image
     - string
     - wsuconnect/simnibs:4.6.0
     - Docker image with charm_brain_print in /usr/bin
   * - extra_args
     - string
     - ""
     - Extra charm_brain_print arguments, e.g. ``--skull -- --brainstem``
   * - request_cpus, request_memory, request_disk
     - int, string, string
     - 4, 16g, 30GB
     - HTCondor resource requests

Minimal entry: ``"simnibs": {"enabled": true}``

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

The project credentials are loaded into the ``creds`` object of the support_tools module (an instance of the ``creds`` class in
``wsuconnect/classes/creds.py``). When support_tools is imported, ``st.creds.projects`` and ``st.creds.masterMachineName`` are set from
credentials.json. Calling ``st.creds.read()`` then sets every key of the selected project as an attribute of ``st.creds``, for example
``st.creds.dataDir`` or ``st.creds.searchTable``. The optional ``simnibs`` entry is reset to its defaults on every ``read()`` and
then merged with the project's values, so ``st.creds.simnibs`` always holds every key and never carries over from a previously read project.

.. code-block:: python

    import support_tools as st
    st.creds.read('<project_identifier>')
    print(st.creds.dataDir)

.. py:method:: creds.read(project)

    Read the selected project's entry from credentials.json in the wsuconnect package's ``data/`` directory and set each of its keys as an
    attribute of ``st.creds``.

    :param project: <project_identifier>. This should correspond to the project's IRB protocol number.
    :type project: str
    :return: True if the project was read, False if credentials.json could not be read or the project is not listed in ``projects``
    :rtype: bool

