:topic: Glossary

********
Glossary
********

This glossary sets the standard spelling and meaning of terms used throughout this manual. Terms related to data organization
follow the `Brain Imaging Data Structure (BIDS) specification <https://bids-specification.readthedocs.io/en/stable/>`__; where a
BIDS definition exists, it is quoted or closely paraphrased from the specification.


Data Organization (BIDS)
========================

.. glossary::

   BIDS
      The Brain Imaging Data Structure, a community standard for organizing and describing neuroimaging and behavioral data.
      Always written in capital letters. See :ref:`data_organization`.

   dataset
      A set of neuroimaging and behavioral data acquired for a purpose of a particular study.

   subject
      A person or animal participating in the study. Used interchangeably with the term *participant*. Identified in filenames
      by the ``sub-<label>`` entity.

   session
      A logical grouping of neuroimaging and behavioral data consistent across subjects. A session commonly corresponds to one
      visit to the MRI scanner. Identified in filenames by the ``ses-<label>`` entity.

   data acquisition
      A continuous uninterrupted block of time during which a brain scanning instrument was acquiring data according to
      particular scanning parameters.

   task
      A set of structured activities performed by the participant. Identified in filenames by the ``task-<label>`` entity.

   run
      An uninterrupted repetition of data acquisition that has the same acquisition parameters and task. Identified in
      filenames by the ``run-<index>`` entity.

   modality
      The category of brain data recorded by a file. For MRI data, different pulse sequences are considered distinct modalities,
      such as ``T1w``, ``bold`` or ``dwi``.

   data type
      A functional group of different types of data, stored as a subdirectory of a session, such as ``anat`` (anatomical),
      ``func`` (functional), ``dwi`` (diffusion-weighted), ``fmap`` (field maps) or ``perf`` (perfusion, including ASL).

   entity
      An attribute that can be associated with a file, contributing to the identification of that file. An entity is written
      in a filename as a key-value pair, ``<key>-<value>``, such as ``sub-001`` or ``task-rest``. Entities MUST appear in the
      order given by the `BIDS entity table <https://bids-specification.readthedocs.io/en/stable/appendices/entity-table.html>`__.

   key
      The short name of an entity that comes before the hyphen in a filename, such as ``sub``, ``ses`` or ``acq``.

   label
      An alphanumeric value (possibly including ``+`` characters) that follows an entity key, such as ``rest`` in ``task-rest``.
      Labels cannot contain underscores (``_``) or hyphens (``-``).

   index
      A nonnegative integer that follows an entity key, possibly prefixed with zeros for consistent indentation, such as ``01``
      in ``run-01``.

   suffix
      An alphanumeric string that forms part of a filename, located after all entities and following a final underscore, such
      as ``T1w`` or ``bold``. The suffix usually indicates the modality.

   file extension
      The portion of the filename after the left-most period (``.``), such as ``.nii.gz`` or ``.json``.

   sidecar JSON
      A JSON file with the same name as a data file (apart from the file extension) that stores the metadata for that data file,
      such as scanning parameters.

   sourcedata
      A directory where data are stored before harmonization, reconstruction or file format conversion. For CoNNECT projects,
      the original :term:`DICOM` images exported from the MRI are stored in ``sourcedata``.

   rawdata
      A directory containing the raw (unprocessed, or minimally processed due to file format conversion) BIDS dataset.
      For CoNNECT projects, :term:`NIfTI` images converted from ``sourcedata`` are organized here.

   derivatives
      Outputs of processing pipelines, such as brain extractions, registrations or statistical maps. Derivatives MUST be kept
      separate from raw data, in the ``derivatives`` directory.


Image Formats and Conversion
============================

.. glossary::

   DICOM
      Digital Imaging and Communications in Medicine, the standard file format and network protocol used by the MRI scanner and
      PACS. Always written in capital letters.

   NIfTI
      Neuroimaging Informatics Technology Initiative, the image file format (``.nii`` or compressed ``.nii.gz``) used for raw
      and processed data in BIDS. Written with a lowercase *f*.

   dcm2niix
      The open-source tool used to convert :term:`DICOM` images to :term:`NIfTI` images and generate :term:`sidecar JSON` files.

   PACS
      Picture Archiving and Communication System, the system that stores and serves medical images in :term:`DICOM` format.


MRI Hardware
============

.. glossary::

   3T
      Three tesla, the magnetic field strength of the CoNNECT MRI scanner, the Philips Ingenia Cx. Written as *3T* or *3 tesla*
      (the unit *tesla* is lowercase when written out; its symbol *T* is uppercase).


Computing and Storage
=====================

.. glossary::

   NPC
      The CoNNECT Neuro-Processing Cluster. See :doc:`cluster_computing/index`.

   jumpbox
      A user-specific virtual machine used to access the :term:`NPC`.

   master node
      The main controller of the :term:`NPC`.

   core node
      A compute node of the :term:`NPC` that runs jobs submitted through :term:`HTCondor`.

   HTCondor
      The job scheduler used to distribute processing across the :term:`NPC`. Written as *HTCondor*.

   storage bucket
      A share on the CoNNECT centralized storage. Access to each bucket is limited to approved users, by IT on the storage
      side and by the mount permissions on the CoNNECT nodes. See :ref:`storage_directory_structure`.

   storage mount
      The local mount of a :term:`storage bucket` on a CoNNECT node, written as ``<storage_mount>`` in this manual.

   Amazon S3
      Amazon Simple Storage Service, the cloud object storage used to store project data.

   S3 bucket
      A container for files (objects) in :term:`Amazon S3`. Written as *S3 bucket*, with a lowercase *b*.

   MySQL
      The relational database system used to index project files. Written as *MySQL*.
