:topic: Custom Support Tools

*********************
CoNNECT Support Tools
*********************

.. contents:: On this page
   :local:
   :depth: 1


Several custom support tools have been created to aid in the batch processing. These tools support parallel processing via :term:`HTCondor` (including its SGE-style ``condor_qsub`` interface), as implemented in the custom batch processing 
described in the previous section.


.. _support_tools_table:

.. list-table:: CoNNECT support tools. *CLI*: the tool can be run from the command line. *Docker*: a connect_*.py script can run
   the tool in the wsuconnect/neuro Docker container through :term:`HTCondor`.
   :widths: 30 10 10 50
   :header-rows: 1

   * - **Tool**
     - **CLI**
     - **Docker**
     - **Function**
   * - :ref:`bids <bids_python>`
     - No
     - No
     - Builds BIDS filenames and reads entity labels from them
   * - :ref:`condor <condor_python>`
     - No
     - No
     - Creates HTCondor submit files (Docker or vanilla universe)
   * - :ref:`convert_dicoms.py <convert_dicoms_python>`
     - Yes
     - Yes
     - Converts DICOM images to NIfTI images with dcm2niix
   * - :ref:`creds <read_creds_python>`
     - No
     - No
     - Reads a project's entry from credentials.json
   * - :ref:`copy_dirs.py <copy_dirs_python>`
     - Yes
     - No
     - Copies or moves directories to one destination
   * - :ref:`dti_flirt.py <dti_flirt_python>`
     - Yes
     - Yes
     - FLIRT registration of DWI images to structural and standard space
   * - :ref:`dti_preprocess_wf.py <dti_preprocess_python>`
     - Yes
     - Yes
     - DWI preprocessing workflow (eddy, DTIFIT)
   * - :ref:`evaluate_source_file_transfer.py <evaluate_source_file_transfer_python>`
     - Yes
     - No
     - Checks that all expected files were transferred for a subject/session
   * - :ref:`feat_full_firstlevel.py <feat_full_firstlevel_python>`
     - Yes
     - Yes
     - Runs FSL FEAT first-level fMRI analysis
   * - :ref:`flirt_pngappend.py <flirt_pngappend>`
     - Yes
     - No
     - Creates a PNG overlay image to check registration
   * - :ref:`flirt.py <flirt_python>`
     - Yes
     - Yes
     - FLIRT registration, with optional brain extraction
   * - :ref:`fsreconall_stage1_wf.py <fsreconall_stage1_python>`
     - Yes
     - Yes
     - FreeSurfer recon-all, stage 1
   * - :ref:`fsreconall_stage2_wf.py <fsreconall_stage2_python>`
     - Yes
     - Yes
     - FreeSurfer recon-all, stages 2 and 3
   * - :ref:`mysql <mysql_python>`
     - No
     - No
     - Queries and updates the project MySQL tables
   * - :ref:`prepare_examcard_html.py <prepare_examcard_html_python>`
     - No
     - No
     - Prepares the HTML header for converted ExamCards
   * - :ref:`remove_dirs.py <remove_dirs_python>`
     - Yes
     - No
     - Deletes directories
   * - :ref:`RestToolbox <RestToolbox_python>`
     - No
     - No
     - REST requests (GET, POST, PUT, DELETE) to the Orthanc PACS



.. _bids_python:

bids
====

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.bids
    :members:


.. _condor_python:

condor
======

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.condor
    :members:
    :special-members:


.. _convert_dicoms_python:

convert_dicoms.py
=================

.. argparse::
   :ref: wsuconnect.support_tools.convert_dicoms.parser
   :prog: convert_dicoms
   :nodefault:
   :nodefaultconst:


Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.convert_dicoms
    :members:
    :special-members:


.. include:: read_credentials.rst

.. _copy_dirs_python:

copy_dirs.py
============

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.copy_dirs
    :members:
    :special-members:


.. _dti_flirt_python:

dti_flirt.py
============

.. argparse::
   :ref: wsuconnect.support_tools.dti_flirt.parser
   :prog: dti_flirt
   :nodefault:
   :nodefaultconst:

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.dti_flirt
    :members:
    :special-members:


.. _dti_preprocess_python:

dti_preprocess_wf.py
====================

.. argparse::
   :ref: wsuconnect.support_tools.dti_preprocess_wf.parser
   :prog: dti_preprocess_wf
   :nodefault:
   :nodefaultconst:

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.dti_preprocess_wf
    :members:
    :special-members:


.. _evaluate_source_file_transfer_python:

evaluate_source_file_transfer.py
================================

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.evaluate_source_file_transfer
    :members:
    :special-members:


.. _feat_full_firstlevel_python:

feat_full_firstlevel.py
=======================

.. argparse::
   :ref: wsuconnect.support_tools.feat_full_firstlevel.parser
   :prog: feat_full_firstlevel
   :nodefault:
   :nodefaultconst:

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.feat_full_firstlevel
    :members:
    :special-members:


.. _flirt_pngappend:

flirt_pngappend.py
==================

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.flirt_pngappend
    :members:
    :special-members:


.. _flirt_python:

flirt.py
========

.. argparse::
   :ref: wsuconnect.support_tools.flirt.parser
   :prog: flirt
   :nodefault:
   :nodefaultconst:

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.flirt
    :members:
    :special-members:


.. _fsreconall_stage1_python:

fsreconall_stage1_wf.py
=======================

.. argparse::
   :ref: wsuconnect.support_tools.fsreconall_stage1.parser
   :prog: fsreconall_stage1
   :nodefault:
   :nodefaultconst:

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.fsreconall_stage1_wf
    :members:
    :special-members:


.. _fsreconall_stage2_python:

fsreconall_stage2_wf.py
=======================

.. argparse::
   :ref: wsuconnect.support_tools.fsreconall_stage2.parser
   :prog: fsreconall_stage2
   :nodefault:
   :nodefaultconst:

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.fsreconall_stage2_wf
    :members:
    :special-members:


.. _mysql_python:

mysql.py
========

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.mysql
    :members:
    :special-members:


.. _prepare_examcard_html_python:

prepare_examcard_html.py
========================

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.prepare_examcard_html
    :members:
    :special-members:


.. _remove_dirs_python:

remove_dirs.py
==============

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.remove_dirs
    :members:
    :special-members:


.. _RestToolbox_python:

RestToolbox.py
==============

.. note:: No command-line interface (CLI) support.

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.RestToolbox
    :members:
    :special-members:




