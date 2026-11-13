.. _simnibs_python:

simnibs
=======

Segments a subject/session with SimNIBS ``charm`` and prepares a print-ready brain (``brain_print.3mf``) in the
``wsuconnect/simnibs`` Docker image, through :term:`HTCondor`. ``connect_pacs_dicom_grabber.py`` calls it automatically for
the sessions selected by a project's ``"simnibs": {"include_sessions": [...]}`` in credentials.json (see :numref:`credentials_simnibs_table`).

How it works
------------

* ``submit_session()`` runs after a subject/session's DICOMs are converted. It finds the T1 (and optional second image)
  in ``rawdata/sub-X/ses-Y/anat`` by the ``t1_label``/``t2_label`` filename endings and runs ``condor_submit`` as the
  project's ``condor_user``. HTCondor will not run jobs owned by root, so the grabber (root) never owns the job.
* No file transfer. Root creates ``<dataDir>/derivatives/sub-X/ses-Y/anat/charm`` (owned by ``condor_user``, storage
  group, mode 2770) and the job runs ``charm_brain_print`` there in the Docker image, reading the images straight from
  rawdata. The project storage is mounted in the container by the ``+MOUNT_RESSHAREnn`` attribute (``dockerMountIf``).
  Results land in ``anat/charm/m2m_sub-X_ses-Y``.
* The submit file, the job script ``run_charm.sh`` and the HTCondor log, output and error files go to
  ``<dataDir>/code/processing_logs/connect_simnibs/sub-X_ses-Y_<time>/``. Job state is kept in ``/var/lib/connect-simnibs``.
* ``run_charm.sh`` always leaves ``m2m_<id>/condor_exit_code``, so a charm failure ends the job with charm's exit code.
* ``collect_finished()`` runs on every grabber loop. When a job ends, the results and logs are set to mode 0770 with the
  storage group (``set_connect_perms``) and the outcome is logged.
* Start, finish, failure, hold and skip lines go to ``/Export/data_transfer_progress/connect_pacs_dicom_grabber-YYYYMM.log``.
* A session is not resubmitted while a job is queued or once ``anat/charm/m2m_sub-X_ses-Y/brain_print.3mf`` exists; delete
  that folder to rerun it. A leftover ``m2m`` folder without ``brain_print.3mf`` is renamed to ``.prev_<time>`` on resubmit.

.. argparse::
   :ref: wsuconnect.connect_simnibs.parser
   :prog: connect_simnibs.py
   :nodefault:
   :nodefaultconst:

Python Implementation
---------------------

.. automodule:: wsuconnect.support_tools.simnibs
    :members:
