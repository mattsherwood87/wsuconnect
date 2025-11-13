:topic: CoNNECT Broad Analysis Tools

****************************
CoNNECT Broad Analysis Tools
****************************

There are many custom analysis tools that have been developed to provide broad processing capabilities across projects, MRI scanners, imaging parameters, and processing 
specifications. These tools are described in this Section. Many of these tools utilize a common JSON architecture to describe project-specific inputs that are utilized 
by these analysis tools to allow maximum flexibility of their implementation. Specifics to these JSON control files can be found at :ref:`project-specific_JSON_control_files`. 

.. note:: At this time, these functions only support cli implementation. 

.. 
    include:: connect_create_project_db.rst
        
    include:: connect_create_raw_nii.rst

    include:: connect_dcm2nii.rst

    include:: connect_flirt.rst


.. _connect_dcm2nii_python:

connect_dcm2nii.py
==================

    
This function converts DICOM images to NIfTI utilizing dcm2niix and :ref:`convert_dicoms_python`. Files within the identified Project's :ref:`searchSourceTable <read_creds_python>`
are queried via MySQL for DICOM images. These DICOM images are contained within the Project's sourcedata directory. Directories within sourcedata that contain DICOM images are then passed to dcm2niix for 
conversion. The NIfTI images created are then stored in the same sourcedata directory as their source DICOM directory.

.. seealso::
    The `dcm2niix <https://www.nitrc.org/plugins/mwiki/index.php/dcm2nii:MainPage>`_ is the most common tool for DICOM-to-NIfTI conversion, and is implemented on our Ubuntu 24.04 CoNNECT NPC nodes.

This function can be executed via cli only:

.. argparse::
   :ref: wsuconnect.connect_dcm2nii.parser
   :prog: connect_dcm2nii
   :nodefault:
   :nodefaultconst:

connect_flirt.py
================

.. argparse::
   :ref: wsuconnect.connect_flirt.parser
   :prog: connect_flirt
   :nodefault:
   :nodefaultconst:
..
    Python Implementation
    ---------------------
    automodule:: wsuconnect.support_tools.feat_full_firstlevel
    :members:
    :special-members:


.. _flirt_pngappend:
..
    .. include:: connect_mri_system_log_grabber.rst

.. include:: connect_neuro_db_query.rst

.. include:: connect_neuro_db_update.rst

.. include:: connect_pacs_dicom_grabber.rst

.. include:: connect_rawdata_check.rst

..
    .. include:: connect_sourcedata_check.rst





