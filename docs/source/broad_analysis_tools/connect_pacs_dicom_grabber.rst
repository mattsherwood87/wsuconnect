


connect_pacs_dicom_grabber.py
==========================

.. _pacs_grabber_diagram:

.. figure:: ../_images/pacs-grabber2.png
   :align: center
   :width: 30%
      
   Sequence diagram for the CoNNECT PACS DICOM grabber Python function.
    

This function moves DICOM images from their local temporary PACS storage location (/resshare/PACS) to their associated sourcedata directory (:numref:`pacs_grabber_sourcedata_directory`), performs DICOM-to-NIfTI conversion via :ref:`convert_dicoms.py <convert_dicoms_python>`, and 
moves the NIfTI images into a BIDS structure within the Project's rawdata directory (:numref:`pacs_grabber_diagram`). The <project_identifier>, subject label, and session label (optional) are extracted from the DICOM header 
Patient's Name (0010,0010) attribute. These elements are space-delimited. The session label is appended to an acquisition date label using the format YYYYMMDD. 


.. _pacs_grabber_sourcedata_directory:

.. figure:: ../_images/pacs-grabber_sourcedata_location.png
   :align: center
   :width: 15%
      
   Final location of source DICOM data following transfer from MRI via Orthanc PACS and connect_pacs_dicom_grabber.py.


.. note:: This function is continuously running in the background on the CoNNECT NPC master node (and loaded at startup) as the pacs-grabber.service.


This function can be executed via the command line only, using the following options. However, make sure the pacs-grabber.service is stopped before running it:

.. code-block:: shell-session

    $ connect_pacs_dicom_grabber.py 

-h, --help  show the help message and exit
-v, --version   display the current version


