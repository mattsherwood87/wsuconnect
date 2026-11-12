.. _simnibs_python:

simnibs
=======

Segments a subject/session with SimNIBS ``charm`` and prepares a print-ready brain (``brain_print.3mf``) in the
``wsuconnect/simnibs`` Docker image, through :term:`HTCondor`. ``connect_pacs_dicom_grabber.py`` calls it automatically for
projects with ``"simnibs": {"enabled": true}`` in credentials.json (see :numref:`credentials_simnibs_table`).

How it works
------------

* ``submit_session()`` runs after a subject/session's DICOMs are converted. It finds the T1w (and T2w, if any) in
  ``rawdata/sub-X/ses-Y/anat``, copies them to a local job folder in ``/var/lib/connect-simnibs`` and runs ``condor_submit``
  as the project's ``condor_user``. HTCondor will not run jobs owned by root, so the grabber (root) never owns the job.
* Inputs and the ``m2m_<id>`` output move by HTCondor file transfer, so the job account never needs rights to the project data.
* ``collect_finished()`` runs on every grabber loop. A finished job's results are copied to
  ``<dataDir>/derivatives/sub-X/ses-Y/anat/charm`` and set to mode 0770 with the storage group (``set_connect_perms``);
  the HTCondor log, output and error files go to ``<dataDir>/code/processing_logs/connect_simnibs/``.
* Start, finish, failure, hold and skip lines go to ``/Export/data_transfer_progress/connect_pacs_dicom_grabber-YYYYMM.log``.
* A session is not resubmitted while a job is queued or once ``anat/charm/brain_print.3mf`` exists; delete that folder to rerun it.

.. argparse::
   :ref: wsuconnect.connect_simnibs.parser
   :prog: connect_simnibs.py
   :nodefault:
   :nodefaultconst:

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.simnibs
    :members:
