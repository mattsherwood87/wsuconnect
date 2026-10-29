.. _connect_pacs_dicom_grabber_python:

connect_pacs_dicom_grabber.py
=============================

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


.. note:: This function is continuously running in the background on the CoNNECT NPC master node (and loaded at startup) as the pacs-grabber.service.


This function can be executed via the command line only, using the following options. However, make sure the pacs-grabber.service is stopped before running it:

.. code-block:: shell-session

    $ connect_pacs_dicom_grabber.py 

-h, --help  show the help message and exit
-v, --version   display the current version


