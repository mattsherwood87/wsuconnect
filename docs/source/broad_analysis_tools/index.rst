:topic: CoNNECT Broad Analysis Tools

****************************
CoNNECT Broad Analysis Tools
****************************

.. contents:: On this page
   :local:
   :depth: 1

There are many custom analysis tools that have been developed to provide broad processing capabilities across projects, MRI scanners, imaging parameters, and processing
specifications. These tools are described in this Section. Many of these tools utilize a common JSON architecture to describe project-specific inputs that are utilized
by these analysis tools to allow maximum flexibility of their implementation. Specifics of these JSON control files can be found in :ref:`json_control_files`.

.. note:: At this time, these programs only support a command-line interface (CLI). The options below are read from each program's help text (``-h``).


Project Setup
=============

Programs to add a new project and create its database tables.

.. _connect_add_project_creds_python:

connect_add_project_creds.py
----------------------------

This program requires PyQt5.

.. argparse::
   :module: wsuconnect.connect_add_project_creds
   :func: parser
   :prog: connect_add_project_creds.py
   :nodefault:
   :nodefaultconst:

.. _connect_update_creds_db_python:

connect_update_creds_db.py
--------------------------

.. argparse::
   :module: wsuconnect.connect_update_creds_db
   :func: parser
   :prog: connect_update_creds_db.py
   :nodefault:
   :nodefaultconst:

.. _connect_create_project_db_python:

connect_create_project_db.py
----------------------------

This program creates the Project's searchTable and searchSourceTable, as defined via the credentials JSON file loaded by :ref:`read_creds_python`.

.. argparse::
   :module: wsuconnect.connect_create_project_db
   :func: parser
   :prog: connect_create_project_db.py
   :nodefault:
   :nodefaultconst:

.. _connect_examcard_conversion_python:

connect_examcard_conversion.py
------------------------------

.. argparse::
   :module: wsuconnect.connect_examcard_conversion
   :func: parser
   :prog: connect_examcard_conversion.py
   :nodefault:
   :nodefaultconst:

Data Transfer and Database
==========================

Programs that move MRI data to centralized storage and keep the MySQL file tables current.

.. _connect_pacs_dicom_grabber_python:

connect_pacs_dicom_grabber.py
-----------------------------

.. _pacs_grabber_diagram:

.. figure:: ../_images/pacs-grabber2.png
   :align: center
   :width: 30%
      
   Sequence diagram for the CoNNECT PACS DICOM grabber Python function.
    

This function completes the PACS data transfer from the MRI scanner to centralized storage (see the PACS section of :doc:`Cluster Computing </cluster_computing/index>`). The MRI scanner
pushes DICOM images to the Orthanc PACS, which writes them to the temporary PACS storage location (``/PACS_m2``) on the NPC
:term:`transfer and execute node` while they are transferred. This function then moves the DICOM images from ``/PACS_m2`` to the subject/session folder in the project's ``sourcedata``
directory on the centralized storage bucket (:numref:`pacs_grabber_sourcedata_directory`), performs DICOM-to-NIfTI conversion via
:ref:`convert_dicoms.py <convert_dicoms_python>`, and moves the NIfTI images into a BIDS structure within the project's ``rawdata``
directory (:numref:`pacs_grabber_diagram`).

The <project_identifier>, subject label, and session label are extracted from the DICOM header Patient's Name (0010,0010)
attribute. These elements are space-delimited, for example ``<project_identifier> <subject_label> <session_label>``. The subject
label sets the ``sub-<label>`` folder and the session label sets the ``ses-<label>`` folder. If the Patient's Name does not include
a session label, the acquisition (study) date is used as the session label in the format YYYYMMDD (``ses-<YYYYMMDD>``). Each DICOM
series is stored in its own folder within the session folder.


.. _pacs_grabber_sourcedata_directory:

.. figure:: ../_images/pacs-grabber_sourcedata_location.png
   :align: center
   :width: 90%
      
   Final location of source DICOM data in the project's centralized storage bucket, following transfer from the MRI via the
   Orthanc PACS and connect_pacs_dicom_grabber.py.

.. note:: This program runs continuously in the background on the CoNNECT NPC master node (and is loaded at startup) as the pacs-grabber.service. Stop the pacs-grabber.service before running it from the command line.

.. argparse::
   :module: wsuconnect.connect_pacs_dicom_grabber
   :func: parser
   :prog: connect_pacs_dicom_grabber.py
   :nodefault:
   :nodefaultconst:

.. _connect_neuro_db_update_python:

connect_neuro_db_update.py
--------------------------

This program searches the project directories to update the main (:ref:`searchTable <read_creds_python>`)
and/or source (:ref:`searchSourceTable <read_creds_python>`) MySQL database tables associated with the specified project.

.. note:: This program runs nightly. Run it after new files are created.

.. argparse::
   :module: wsuconnect.connect_neuro_db_update
   :func: parser
   :prog: connect_neuro_db_update.py
   :nodefault:
   :nodefaultconst:

.. _connect_neuro_db_query_python:

connect_neuro_db_query.py
-------------------------

This program queries the Project's MySQL :ref:`searchTable or searchSourceTable <read_creds_python>` using the search criteria defined below.

.. argparse::
   :module: wsuconnect.connect_neuro_db_query
   :func: parser
   :prog: connect_neuro_db_query.py
   :nodefault:
   :nodefaultconst:

BIDS Rawdata
============

Programs that build and check a project's BIDS rawdata directory.

.. _connect_dcm2nii_python:

connect_dcm2nii.py
------------------

This program converts DICOM images to NIfTI images using dcm2niix and :ref:`convert_dicoms_python`. Files within the identified Project's :ref:`searchSourceTable <read_creds_python>`
are queried via MySQL for DICOM images. These DICOM images are contained within the Project's sourcedata directory. Directories within sourcedata that contain DICOM images are then passed to dcm2niix for
conversion. The NIfTI images created are then stored in the same sourcedata directory as their source DICOM directory.

.. seealso::
    `dcm2niix <https://www.nitrc.org/plugins/mwiki/index.php/dcm2nii:MainPage>`_ is the most common tool for DICOM-to-NIfTI conversion, and is implemented on our Ubuntu 24.04 CoNNECT NPC nodes.

.. argparse::
   :module: wsuconnect.connect_dcm2nii
   :func: parser
   :prog: connect_dcm2nii.py
   :nodefault:
   :nodefaultconst:

.. _connect_create_raw_nii_python:

connect_create_raw_nii.py
-------------------------

This program moves NIfTI images in sourcedata (and their sidecar JSON and text files) created by :ref:`connect_dcm2nii_python` or :ref:`convert_dicoms_python` to the corresponding rawdata directory.

.. _project_code_directory:

.. figure:: ../_images/connect_create_raw_nii.png
   :align: center
   :width: 20%

   Required prerequisite files for execution of connect_create_raw_nii.py.

.. argparse::
   :module: wsuconnect.connect_create_raw_nii
   :func: parser
   :prog: connect_create_raw_nii.py
   :nodefault:
   :nodefaultconst:

.. _connect_add_sidecar_key_python:

connect_add_sidecar_key.py
--------------------------

.. argparse::
   :module: wsuconnect.connect_add_sidecar_key
   :func: parser
   :prog: connect_add_sidecar_key.py
   :nodefault:
   :nodefaultconst:

.. _connect_mod_sidecar_key_python:

connect_mod_sidecar_key.py
--------------------------

.. argparse::
   :module: wsuconnect.connect_mod_sidecar_key
   :func: parser
   :prog: connect_mod_sidecar_key.py
   :nodefault:
   :nodefaultconst:

.. _connect_rename_rawdata_python:

connect_rename_rawdata.py
-------------------------

.. argparse::
   :module: wsuconnect.connect_rename_rawdata
   :func: parser
   :prog: connect_rename_rawdata.py
   :nodefault:
   :nodefaultconst:

.. _connect_rawdata_check_python:

connect_rawdata_check.py
------------------------

This program creates a table indicating the absence (0) or presence (1) of MRI raw data (NIfTI images) in rawdata. Raw data are identified via the project's
:ref:`scan ID JSON control file <scan_id_json>`. An output table in CSV format is created in the Project's 'processing_logs' directory titled
<project_identifier>_rawdata_check.csv.

.. argparse::
   :module: wsuconnect.connect_rawdata_check
   :func: parser
   :prog: connect_rawdata_check.py
   :nodefault:
   :nodefaultconst:

.. _connect_derivatives_check_python:

connect_derivatives_check.py
----------------------------

.. argparse::
   :module: wsuconnect.connect_derivatives_check
   :func: parser
   :prog: connect_derivatives_check.py
   :nodefault:
   :nodefaultconst:

Logs and Scan Time
==================

Programs that collect experiment logs, MRI system logs and physiological recordings, and report scan time.

.. _connect_exp_log_grabber_p1_python:

connect_exp_log_grabber_p1.py
-----------------------------

.. note:: This program runs on the MRI stimulus computer, not on the CoNNECT NPC.

.. argparse::
   :module: wsuconnect.connect_exp_log_grabber_p1
   :func: parser
   :prog: connect_exp_log_grabber_p1.py
   :nodefault:
   :nodefaultconst:

.. _connect_exp_log_grabber_p2_python:

connect_exp_log_grabber_p2.py
-----------------------------

.. argparse::
   :module: wsuconnect.connect_exp_log_grabber_p2
   :func: parser
   :prog: connect_exp_log_grabber_p2.py
   :nodefault:
   :nodefaultconst:

.. _connect_mri_system_log_grabber_python:

connect_mri_system_log_grabber.py
---------------------------------

.. argparse::
   :module: wsuconnect.connect_mri_system_log_grabber
   :func: parser
   :prog: connect_mri_system_log_grabber.py
   :nodefault:
   :nodefaultconst:

.. _connect_mri_system_log_grabber_p2_python:

connect_mri_system_log_grabber_p2.py
------------------------------------

.. argparse::
   :module: wsuconnect.connect_mri_system_log_grabber_p2
   :func: parser
   :prog: connect_mri_system_log_grabber_p2.py
   :nodefault:
   :nodefaultconst:

.. _connect_physio_extraction_python:

connect_physio_extraction.py
----------------------------

.. argparse::
   :module: wsuconnect.connect_physio_extraction
   :func: parser
   :prog: connect_physio_extraction.py
   :nodefault:
   :nodefaultconst:

.. _connect_scantime_evaluator_python:

connect_scantime_evaluator.py
-----------------------------

.. argparse::
   :module: wsuconnect.connect_scantime_evaluator
   :func: parser
   :prog: connect_scantime_evaluator.py
   :nodefault:
   :nodefaultconst:

Processing Pipelines
====================

Programs that run preprocessing and analysis pipelines, most of which can submit jobs to HTCondor.

.. _connect_aslprep_python:

connect_aslprep.py
------------------

.. argparse::
   :module: wsuconnect.connect_aslprep
   :func: parser
   :prog: connect_aslprep.py
   :nodefault:
   :nodefaultconst:

.. _connect_fmriprep_python:

connect_fmriprep.py
-------------------

.. argparse::
   :module: wsuconnect.connect_fmriprep
   :func: parser
   :prog: connect_fmriprep.py
   :nodefault:
   :nodefaultconst:

.. _connect_recon-all_python:

connect_recon-all.py
--------------------

.. argparse::
   :module: wsuconnect.connect_recon-all
   :func: parser
   :prog: connect_recon-all.py
   :nodefault:
   :nodefaultconst:

.. _connect_feat_full_firstlevel_python:

connect_feat_full_firstlevel.py
-------------------------------

.. argparse::
   :module: wsuconnect.connect_feat_full_firstlevel
   :func: parser
   :prog: connect_feat_full_firstlevel.py
   :nodefault:
   :nodefaultconst:

.. _connect_flirt_python:

connect_flirt.py
----------------

.. argparse::
   :module: wsuconnect.connect_flirt
   :func: parser
   :prog: connect_flirt.py
   :nodefault:
   :nodefaultconst:

.. _connect_dti_preprocess_python:

connect_dti_preprocess.py
-------------------------

.. argparse::
   :module: wsuconnect.connect_dti_preprocess
   :func: parser
   :prog: connect_dti_preprocess.py
   :nodefault:
   :nodefaultconst:

.. _connect_dti_flirt_python:

connect_dti_flirt.py
--------------------

.. argparse::
   :module: wsuconnect.connect_dti_flirt
   :func: parser
   :prog: connect_dti_flirt.py
   :nodefault:
   :nodefaultconst:

.. _connect_slicer_python:

connect_slicer.py
-----------------

.. argparse::
   :module: wsuconnect.connect_slicer
   :func: parser
   :prog: connect_slicer.py
   :nodefault:
   :nodefaultconst:

.. _connect_generate_stl_python:

connect_generate_stl.py
-----------------------

.. argparse::
   :module: wsuconnect.connect_generate_stl
   :func: parser
   :prog: connect_generate_stl.py
   :nodefault:
   :nodefaultconst:

.. _connect_zmap_cifti_python:

connect_zmap_cifti.py
---------------------

.. argparse::
   :module: wsuconnect.connect_zmap_cifti
   :func: parser
   :prog: connect_zmap_cifti.py
   :nodefault:
   :nodefaultconst:

Statistics and Quality Control
==============================

Programs that compute and combine regional statistics and quality control measures across participants.

.. _connect_compute_segstats_python:

connect_compute_segstats.py
---------------------------

.. argparse::
   :module: wsuconnect.connect_compute_segstats
   :func: parser
   :prog: connect_compute_segstats.py
   :nodefault:
   :nodefaultconst:

.. _connect_compute_cifti_segstats_python:

connect_compute_cifti_segstats.py
---------------------------------

.. argparse::
   :module: wsuconnect.connect_compute_cifti_segstats
   :func: parser
   :prog: connect_compute_cifti_segstats.py
   :nodefault:
   :nodefaultconst:

.. _connect_extract_segstats_python:

connect_extract_segstats.py
---------------------------

.. argparse::
   :module: wsuconnect.connect_extract_segstats
   :func: parser
   :prog: connect_extract_segstats.py
   :nodefault:
   :nodefaultconst:

.. _connect_organize_segstats_python:

connect_organize_segstats.py
----------------------------

.. argparse::
   :module: wsuconnect.connect_organize_segstats
   :func: parser
   :prog: connect_organize_segstats.py
   :nodefault:
   :nodefaultconst:

.. _connect_combine_cbf_qc_python:

connect_combine_cbf_qc.py
-------------------------

.. argparse::
   :module: wsuconnect.connect_combine_cbf_qc
   :func: parser
   :prog: connect_combine_cbf_qc.py
   :nodefault:
   :nodefaultconst:

.. _connect_combine_feat_mc_rms_python:

connect_combine_feat_mc_rms.py
------------------------------

.. argparse::
   :module: wsuconnect.connect_combine_feat_mc_rms
   :func: parser
   :prog: connect_combine_feat_mc_rms.py
   :nodefault:
   :nodefaultconst:

.. _connect_combine_fmriprep_fd_python:

connect_combine_fmriprep_fd.py
------------------------------

.. argparse::
   :module: wsuconnect.connect_combine_fmriprep_fd
   :func: parser
   :prog: connect_combine_fmriprep_fd.py
   :nodefault:
   :nodefaultconst:

.. _connect_split_aslprep_report_python:

connect_split_aslprep_report.py
-------------------------------

.. argparse::
   :module: wsuconnect.connect_split_aslprep_report
   :func: parser
   :prog: connect_split_aslprep_report.py
   :nodefault:
   :nodefaultconst:

.. _connect_build_report_python:

connect_build_report.py
-----------------------

.. argparse::
   :module: wsuconnect.connect_build_report
   :func: parser
   :prog: connect_build_report.py
   :nodefault:
   :nodefaultconst:
